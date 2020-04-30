using Microsoft.AspNetCore.Hosting;
using Microsoft.AspNetCore.Builder;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Logging;
using System;
using System.IO;
using MongoDB.Driver;
using System.Security.Authentication;

namespace Homework3 {
    public class Program {
        public static IHostingEnvironment HostingEnvironment { get; private set; }
        public static IConfiguration Configuration { get; private set; }

        public static void Main(string[] args) {
            var host = new WebHostBuilder()
                .UseKestrel()
                .UseContentRoot(Directory.GetCurrentDirectory())
                .UseIISIntegration()
                .ConfigureAppConfiguration((context, configBuilder) => {
                    HostingEnvironment = context.HostingEnvironment;

                    configBuilder.SetBasePath(HostingEnvironment.ContentRootPath)
                        .AddJsonFile("appsettings.json", optional: true, reloadOnChange: true)
                        .AddJsonFile($"appsettings.{HostingEnvironment.EnvironmentName}.json", optional: true)
                        .AddEnvironmentVariables();

                    Configuration = configBuilder.Build();
                })
                .ConfigureServices(services => {
                    services.AddMvc();
                    services.AddSpaStaticFiles();
                })
                .ConfigureLogging(loggingBuilder => {
                    loggingBuilder.AddConfiguration(Configuration.GetSection("Logging"));
                    if (HostingEnvironment.IsDevelopment()) {
                        // Only use Console and Debug logging during development.
                        loggingBuilder.AddConsole(options =>
                            options.IncludeScopes = Configuration.GetValue<bool>("Logging:IncludeScopes"));
                        loggingBuilder.AddDebug();
                    }
                })
                .Configure((app) => {
                    var logger = app.ApplicationServices.GetService<ILoggerFactory>().CreateLogger("Startup");

                    app.UseStaticFiles();
                    app.UseMvc();
                })
                .Build();

            host.Run();
        }
    }
}
