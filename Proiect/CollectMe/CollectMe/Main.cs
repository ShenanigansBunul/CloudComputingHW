using Newtonsoft.Json;
using System;
using System.Collections.Generic;
using System.Net.Http;
using System.Threading.Tasks;
using System.Windows.Forms;

namespace CollectMe {
    public partial class Main : Form {
        private HttpClient httpClient = new HttpClient();

        public Main() {
            InitializeComponent();
        }

        private async void okTextBox_Click(object sender, EventArgs e) {
            var id = idTextBox.Text;
            var response = await httpClient.GetStringAsync($"http://127.0.0.1:3421/user/{id}");
            var info = JsonConvert.DeserializeObject<UserInfoResponse>(response);

            var form = new UserInfo(info);
            form.Show();
        }
    }

    public class UserInfoData {
        public string last_known_name;
        public int money;
    }

    public class Collectible {
        public string name;
        public byte[] photo;
    }

    public class UserInfoResponse {
        public UserInfoData user;
        public List<Collectible> collectibles;
    }
}
