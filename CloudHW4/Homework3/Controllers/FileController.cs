using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Security.Authentication;
using System.Threading.Tasks;
using Azure.Storage.Blobs;
using Microsoft.AspNetCore.Http;
using Microsoft.AspNetCore.Mvc;
using Microsoft.Azure.CognitiveServices.Vision.ComputerVision;
using MongoDB.Bson;
using MongoDB.Bson.Serialization.Attributes;
using MongoDB.Driver;
using Newtonsoft.Json;
using SendGrid;
using SendGrid.Helpers.Mail;
using TextKeyPhrases;

namespace Homework3.Controllers {
    public class AddRequest {
        public string Name { get; set; }
        public string Description { get; set; }
    }

    public class AddResponse {
        public string Uuid { get; set; }
        public string UploadUrl { get; set; }
    }

    public class ErrorResponse {
        public string Error { get; set; }
    }

    public class ImageTagsData {
        public string Name { get; set; }
        public int Score { get; set; }
    }

    public class QueryResponse {
        [BsonId]
        public ObjectId Id { get; set; }
        public string Uuid { get; set; }
        public string Name { get; set; }
        public string Description { get; set; }
        public List<string> DescriptionKeyPhrases { get; set; }
        public DateTime Created { get; set; }
        public List<ImageTagsData> Tags { get; set; }
    }

    [Route("api/[controller]")]
    [ApiController]
    public class FileController : ControllerBase {
        private const string DATASTORE_NAMESPACE = "mynamesapce";

        private const string BASE_URL = "http://localhost:5000";
        //private const string BASE_URL = "https://claud-12345.appspot.com";

        [HttpGet("{*url}", Order = int.MaxValue)]
        public ErrorResponse CatchAll() {
            Response.StatusCode = StatusCodes.Status404NotFound;
            return new ErrorResponse {
                Error = "what are you trying to do ?"
            };
        }

        [HttpPost("add")]
        public async Task<AddResponse> Add([FromBody] AddRequest request) {
            var mongo = GetMongoClient();
            var files = mongo.GetCollection<QueryResponse>("files");

            var guid = Guid.NewGuid();
            var uuid = guid.ToString();
            var query = new QueryResponse {
                Uuid = uuid,
                Name = request.Name,
                Description = request.Description,
                Created = DateTime.UtcNow,
                DescriptionKeyPhrases = await TextKeyPhrases.TextKeyPhrases.GetKeyPhrases(request.Description)
            };

            await files.InsertOneAsync(query);

            return new AddResponse {
                Uuid = uuid,
                UploadUrl = $"/api/file/upload/uuid/{uuid}"
            };
        }

        private async Task<List<ImageTagsData>> GetTags(byte[] bytes) {
            try {
                var client = GetVisionClient();
                var analysis = await client.TagImageInStreamAsync(new MemoryStream(bytes));
                var tags = analysis.Tags.ToList();

                return tags.Select(x => new ImageTagsData {
                    Name = x.Name,
                    Score = (int)(x.Confidence * 100)
                }).ToList();
            } catch (Exception) {
                return new List<ImageTagsData>();
            }
        }

        [HttpPost("upload/uuid/{uuid}")]
        public async Task<object> Upload(string uuid) {
            var mongo = GetMongoClient();
            var files = mongo.GetCollection<QueryResponse>("files");

            var filter = Builders<QueryResponse>.Filter.Eq("Uuid", uuid);
            var r = await (await files.FindAsync(filter)).FirstOrDefaultAsync();

            if (r == null) {
                return new ErrorResponse {
                    Error = "no file with that uuid known"
                };
            }

            if (r.Tags != null) {
                return new ErrorResponse {
                    Error = "file already uploaded"
                };
            }

            var blob = GetStorageClient();
            var bytesStream = new MemoryStream();
            await Request.Body.CopyToAsync(bytesStream);

            bytesStream = new MemoryStream(bytesStream.ToArray());

            r.Tags = await GetTags(bytesStream.ToArray());
            await blob.UploadBlobAsync(r.Uuid, bytesStream);

            var updateFilter = Builders<QueryResponse>.Update.Set("Tags", r.Tags);
            await files.UpdateOneAsync(filter, updateFilter);

            return new ErrorResponse {
                Error = "success"
            };
        }

        [HttpGet("data/name/{name}")]
        public async Task<ActionResult> Data(string name) {
            var storage = GetStorageClient();
            var blob = storage.GetBlobClient(name);

            var download = await blob.DownloadAsync();
            var stream = new MemoryStream();
            await download.Value.Content.CopyToAsync(stream);
            stream.Position = 0;

            return File(stream, "application/octet-stream");
        }

        [HttpGet("query/uuid/{uuid}/email/{email}")]
        public async Task<object> Query(string uuid, string email = null) {
            var storage = GetStorageClient();
            try {
                var blob = storage.GetBlobClient(uuid);

                var download = await blob.DownloadAsync();
                var stream = new MemoryStream();
                await download.Value.Content.CopyToAsync(stream);
            } catch (Exception) {
                return new ErrorResponse {
                    Error = "no file with that uuid"
                };
            }

            var mongo = GetMongoClient();
            var files = mongo.GetCollection<QueryResponse>("files");

            var filter = Builders<QueryResponse>.Filter.Eq("Uuid", uuid);
            var found = await (await files.FindAsync(filter)).FirstOrDefaultAsync();

            if (email != null && email.Contains('@')) {
                await SendEmail(email, JsonConvert.SerializeObject(found, Formatting.Indented));
            }

            return found;
        }

        [HttpGet("last/{n}/email/{email}")]
        public async Task<object> Last(string n, string email = null) {
            var mongo = GetMongoClient();
            var files = mongo.GetCollection<QueryResponse>("files");

            var values = await files.Find(new BsonDocument()).ToListAsync();
            values.Sort((x, y) => y.Created.CompareTo(x.Created));
            values = values.Take(int.Parse(n)).ToList();

            var result = new List<object>();
            foreach (var i in values) {
                result.Add(await Query(i.Uuid));
            }

            if (email != null && email.Contains('@')) {
                await SendEmail(email, JsonConvert.SerializeObject(result, Formatting.Indented));
            }

            return result;
        }

        private async Task SendEmail(string email, string text) {
            var apiKey = "";
            var client = new SendGridClient(apiKey);
            var from = new EmailAddress("shenanigansbunul@tachyon.tk", "Shenanigans Bunul");
            var subject = "Azure is fun !";
            var to = new EmailAddress(email);
            var msg = MailHelper.CreateSingleEmail(from, to, subject, text, null);
            await client.SendEmailAsync(msg);
        }

        private IMongoDatabase GetMongoClient() {
            string connectionString =
  @"";
            var settings = MongoClientSettings.FromUrl(
              new MongoUrl(connectionString)
            );
            settings.SslSettings =
              new SslSettings() { EnabledSslProtocols = SslProtocols.Tls12 };
            var client = new MongoClient(settings);
            var db = client.GetDatabase("hello");
            return db;
        }

        private BlobContainerClient GetStorageClient() {
            var connectionString = "DefaultEndpointsProtocol=https;AccountName=stiitu;AccountKey=;EndpointSuffix=core.windows.net";
            BlobServiceClient blobServiceClient = new BlobServiceClient(connectionString);

            BlobContainerClient containerClient = blobServiceClient.GetBlobContainerClient("files");
            return containerClient;
        }

        private ComputerVisionClient GetVisionClient() {
            var key = "";
            var client = new ComputerVisionClient(new ApiKeyServiceClientCredentials(key), new System.Net.Http.DelegatingHandler[] { }) {
                Endpoint = "https://stiitu.cognitiveservices.azure.com/"
            };

            return client;
        }
    }
}
