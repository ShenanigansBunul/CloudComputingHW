namespace CollectMe {
    partial class Main {
        /// <summary>
        /// Required designer variable.
        /// </summary>
        private System.ComponentModel.IContainer components = null;

        /// <summary>
        /// Clean up any resources being used.
        /// </summary>
        /// <param name="disposing">true if managed resources should be disposed; otherwise, false.</param>
        protected override void Dispose(bool disposing) {
            if (disposing && (components != null)) {
                components.Dispose();
            }
            base.Dispose(disposing);
        }

        #region Windows Form Designer generated code

        /// <summary>
        /// Required method for Designer support - do not modify
        /// the contents of this method with the code editor.
        /// </summary>
        private void InitializeComponent() {
            this.idTextBox = new System.Windows.Forms.TextBox();
            this.okTextBox = new System.Windows.Forms.Button();
            this.SuspendLayout();
            // 
            // idTextBox
            // 
            this.idTextBox.Location = new System.Drawing.Point(12, 12);
            this.idTextBox.Name = "idTextBox";
            this.idTextBox.Size = new System.Drawing.Size(166, 20);
            this.idTextBox.TabIndex = 0;
            // 
            // okTextBox
            // 
            this.okTextBox.Location = new System.Drawing.Point(58, 50);
            this.okTextBox.Name = "okTextBox";
            this.okTextBox.Size = new System.Drawing.Size(75, 23);
            this.okTextBox.TabIndex = 1;
            this.okTextBox.Text = "Ok";
            this.okTextBox.UseVisualStyleBackColor = true;
            this.okTextBox.Click += new System.EventHandler(this.okTextBox_Click);
            // 
            // Main
            // 
            this.AutoScaleDimensions = new System.Drawing.SizeF(6F, 13F);
            this.AutoScaleMode = System.Windows.Forms.AutoScaleMode.Font;
            this.ClientSize = new System.Drawing.Size(190, 85);
            this.Controls.Add(this.okTextBox);
            this.Controls.Add(this.idTextBox);
            this.Name = "Main";
            this.Text = "CollectMe";
            this.ResumeLayout(false);
            this.PerformLayout();

        }

        #endregion

        private System.Windows.Forms.TextBox idTextBox;
        private System.Windows.Forms.Button okTextBox;
    }
}

