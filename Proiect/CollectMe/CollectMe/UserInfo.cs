using System.Drawing;
using System.IO;
using System.Windows.Forms;

namespace CollectMe {
    public partial class UserInfo : Form {
        public UserInfo(UserInfoResponse info) {
            InitializeComponent();

            nameTextBox.Text = info.user.last_known_name;
            moneyTextBox.Text = $"{info.user.money} jerrygold";

            var imageList = new ImageList();
            foreach (var i in info.collectibles) {
                Image image;
                if (i.photo == null) {
                    image = new Bitmap(1, 1);
                } else {
                    image = Image.FromStream(new MemoryStream(i.photo));
                }
                imageList.Images.Add(i.name, image);

            }

            listView1.LargeImageList = imageList;
            listView1.View = View.LargeIcon;

            for (int i = 0; i < imageList.Images.Count; ++i) {
                var item = new ListViewItem {
                    ImageIndex = i,
                    Text = info.collectibles[i].name
                };
                listView1.Items.Add(item);
            }
        }
    }
}