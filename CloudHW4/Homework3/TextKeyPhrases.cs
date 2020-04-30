using System;
using System.Collections.Generic;
using System.Linq;
using System.Net;
using System.Net.Http;
using System.Text;
using System.Threading.Tasks;
using Newtonsoft.Json;

namespace TextKeyPhrases {
    public class TextKeyPhrases {

        public static async Task<List<string>> GetKeyPhrases(string text) {
            var endpoint = "https://stiueu.cognitiveservices.azure.com" + "/text/analytics/v2.1/keyPhrases";
            var subscriptionKey = "";

            var inputDocuments = new TextAnalyticsBatchInput() {
                Documents = new List<TextAnalyticsInput>() {
                    new TextAnalyticsInput() {
                        Id = "1",
                        Text = text
                    }
                }
            };

            using (var httpClient = new HttpClient()) {
                httpClient.DefaultRequestHeaders.Add("Ocp-Apim-Subscription-Key", subscriptionKey);

                var httpContent = new StringContent(JsonConvert.SerializeObject(inputDocuments), Encoding.UTF8, "application/json");

                var httpResponse = await httpClient.PostAsync(new Uri(endpoint), httpContent);
                var responseContent = await httpResponse.Content.ReadAsStringAsync();

                if (!httpResponse.StatusCode.Equals(HttpStatusCode.OK) || httpResponse.Content == null) {
                    throw new Exception(responseContent);
                }

                var response = JsonConvert.DeserializeObject<SentimentV3Response>(responseContent, new JsonSerializerSettings() { NullValueHandling = NullValueHandling.Ignore });

                return response.Documents.SelectMany(x => x.KeyPhrases).ToList();
            }
        }

        public class SentimentV3Response {
            public IList<DocumentSentiment> Documents { get; set; }
        }

        public class TextAnalyticsBatchInput {
            public IList<TextAnalyticsInput> Documents { get; set; }
        }

        public class TextAnalyticsInput {
            /// <summary>
            /// A unique, non-empty document identifier.
            /// </summary>
            public string Id { get; set; }

            /// <summary>
            /// The input text to process.
            /// </summary>
            public string Text { get; set; }

            /// <summary>
            /// The language code. Default is english ("en").
            /// </summary>
            public string LanguageCode { get; set; } = "en";
        }

        public class DocumentSentiment {
            public string Id { get; set; }

            public List<string> KeyPhrases { get; set; }
        }
    }
}