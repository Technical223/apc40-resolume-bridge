using System;
using System.IO;
using System.Linq;
using System.Text;
using System.Drawing;
using System.Diagnostics;
using System.Collections.Generic;
using System.Threading;
using System.Threading.Tasks;
using System.Windows.Forms;
using System.Web.Script.Serialization;

[assembly: System.Reflection.AssemblyTitle("APC40 Bridge")]
[assembly: System.Reflection.AssemblyProduct("APC40 Bridge")]
[assembly: System.Reflection.AssemblyCompany("Technical223")]
[assembly: System.Reflection.AssemblyVersion("1.5.3.0")]
[assembly: System.Reflection.AssemblyFileVersion("1.5.3.0")]

namespace ApcBridge {
    static class Program {
        internal static int VisualizerMessage;
        [System.Runtime.InteropServices.DllImport("user32.dll",CharSet=System.Runtime.InteropServices.CharSet.Unicode)]static extern int RegisterWindowMessage(string message);
        [System.Runtime.InteropServices.DllImport("user32.dll")]static extern bool PostMessage(IntPtr window,int message,IntPtr w,IntPtr l);
        [STAThread] static void Main(string[] args) {
            Application.EnableVisualStyles();
            Application.SetCompatibleTextRenderingDefault(false);
            string home = AppDomain.CurrentDomain.BaseDirectory.TrimEnd(Path.DirectorySeparatorChar);
            if (args.Contains("--autostart")) {
                try { Backend.Run(home, "manage.ps1", "-Action start", 60000); }
                catch (Exception ex) { try { File.AppendAllText(Path.Combine(home, "management.log"), DateTime.Now.ToString("s") + " ERROR " + ex.Message + Environment.NewLine); } catch {} }
                return;
            }
            bool created;
            string key = Convert.ToBase64String(System.Security.Cryptography.SHA256.Create().ComputeHash(Encoding.UTF8.GetBytes(home.ToLowerInvariant()))).Replace("/", "_");
            VisualizerMessage=RegisterWindowMessage("APC40Bridge.Visualizer."+key);
            using (var mutex = new Mutex(true, "Local\\APC40ControlPanel_" + key, out created)) {
                if (!created) { if(args.Contains("--visualizer"))PostMessage(new IntPtr(0xffff),VisualizerMessage,IntPtr.Zero,IntPtr.Zero);else MessageBox.Show("The bridge dashboard is already open.", "APC40 Bridge", MessageBoxButtons.OK, MessageBoxIcon.Information);return; }
                Application.Run(new Dashboard(home,args.Contains("--studio"),args.Contains("--visualizer")));
            }
        }
    }
    static class Backend {
        public static JavaScriptSerializer Json { get { return new JavaScriptSerializer(); } }
        public static string Quote(string value) { return "\"" + value + "\""; }
        public static string Run(string home, string script, string args, int timeout) {
            var info = new ProcessStartInfo(Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.System), "WindowsPowerShell\\v1.0\\powershell.exe"),
                "-NoProfile -NonInteractive -ExecutionPolicy Bypass -File " + Quote(Path.Combine(home, script)) + " " + args);
            info.WorkingDirectory = home;
            info.UseShellExecute = false;
            info.CreateNoWindow = true;
            info.RedirectStandardOutput = true;
            info.RedirectStandardError = true;
            info.StandardOutputEncoding = Encoding.UTF8;
            info.StandardErrorEncoding = Encoding.UTF8;
            using (var process = Process.Start(info)) {
                Task<string> output = process.StandardOutput.ReadToEndAsync();
                Task<string> error = process.StandardError.ReadToEndAsync();
                if (!process.WaitForExit(timeout)) { try { process.Kill(); } catch {} throw new Exception("The operation is taking too long. Check the logs for details."); }
                string text = output.Result.Trim();
                string stderr = error.Result.Trim();
                if (process.ExitCode != 0) {
                    try { var result = Json.Deserialize<Dictionary<string, object>>(text); throw new ApplicationException(Convert.ToString(result["message"])); }
                    catch (ApplicationException) { throw; } catch {}
                    throw new Exception(Tail((text + "\n" + stderr).Trim(), 1500));
                }
                return text;
            }
        }
        public static Dictionary<string, object> Action(string home, string action) {
            return Json.Deserialize<Dictionary<string, object>>(Run(home, "manage.ps1", "-Action " + action, 60000));
        }
        public static bool Flag(Dictionary<string, object> value, string key) { return value.ContainsKey(key) && value[key] is bool && (bool)value[key]; }
        public static string Tail(string text, int length) { return text.Length <= length ? text : text.Substring(text.Length-length); }
        public static string LastSession(string home) {
            try {
                var data=Json.Deserialize<Dictionary<string,object>>(File.ReadAllText(Path.Combine(home,"last-session.json")));
                return "Last saved Arena setup: "+Convert.ToString(data["composition"])+"  |  MIDI: "+Convert.ToString(data["mapping"]);
            }catch{return "Last saved Arena setup: not recorded yet";}
        }
        public static string ReadLog(string file) {
            if (!File.Exists(file)) return "No log entries yet.";
            using (var stream = new FileStream(file, FileMode.Open, FileAccess.Read, FileShare.ReadWrite | FileShare.Delete)) {
                bool partial = stream.Length > 64000;
                if (partial) stream.Seek(-64000, SeekOrigin.End);
                using (var reader = new StreamReader(stream, Encoding.UTF8)) {
                    if (partial) reader.ReadLine();
                    return reader.ReadToEnd();
                }
            }
        }
    }
    static class Theme {
        public static Color Bg = Color.FromArgb(18,22,28), Card = Color.FromArgb(29,35,44), Muted = Color.FromArgb(154,167,184),
            Text = Color.FromArgb(238,243,249), Accent = Color.FromArgb(105,229,181), Line = Color.FromArgb(51,62,76);
        public static Label Label(string text, float size, Color color) {
            return new Label { Text=text, ForeColor=color, Font=new Font("Segoe UI",Math.Max(10,size),FontStyle.Regular), AutoSize=false, Dock=DockStyle.Fill, TextAlign=ContentAlignment.MiddleLeft };
        }
        public static Button Button(string text, bool primary) {
            var b = new ModernButton { Text=text, Dock=DockStyle.Fill, FlatStyle=FlatStyle.Flat, Height=44, Cursor=Cursors.Hand,
                ForeColor=primary ? Bg : Text, BackColor=primary ? Accent : Card, Font=new Font("Segoe UI",10,FontStyle.Regular),
                Margin=new Padding(0,0,10,0), UseVisualStyleBackColor=false };
            b.FlatAppearance.BorderSize=primary ? 0 : 1;
            b.FlatAppearance.BorderColor=Line;
            b.FlatAppearance.MouseOverBackColor=primary ? Color.FromArgb(137,242,202) : Color.FromArgb(43,52,65);
            return b;
        }
        public static void Form(Form f, string title, Size size) {
            f.Text=title; f.ClientSize=size; f.BackColor=Bg; f.ForeColor=Text;
            f.Font=new Font("Segoe UI",10); f.StartPosition=FormStartPosition.CenterScreen;
            f.AutoScaleMode=AutoScaleMode.Dpi;
            f.HandleCreated+=(sender,e)=>{try{int enabled=1;DwmSetWindowAttribute(f.Handle,20,ref enabled,4);}catch{}};
            try { f.Icon=Icon.ExtractAssociatedIcon(Application.ExecutablePath); } catch {}
        }
        [System.Runtime.InteropServices.DllImport("dwmapi.dll")]static extern int DwmSetWindowAttribute(IntPtr window,int attribute,ref int value,int size);
        public static TextBox Input(string value) {
            return new TextBox { Text=value, Dock=DockStyle.Fill, BackColor=Card, ForeColor=Text, BorderStyle=BorderStyle.FixedSingle, Margin=new Padding(0,8,0,8) };
        }
    }
    sealed class ModernButton : Button {
        bool hover;
        public ModernButton(){SetStyle(ControlStyles.UserPaint|ControlStyles.AllPaintingInWmPaint|ControlStyles.OptimizedDoubleBuffer|ControlStyles.ResizeRedraw,true);}
        protected override void OnMouseEnter(EventArgs e){base.OnMouseEnter(e);hover=true;Invalidate();}
        protected override void OnMouseLeave(EventArgs e){base.OnMouseLeave(e);hover=false;Invalidate();}
        protected override void OnPaint(PaintEventArgs e){
            var g=e.Graphics;g.Clear(Parent==null?Theme.Bg:Parent.BackColor);g.SmoothingMode=System.Drawing.Drawing2D.SmoothingMode.AntiAlias;
            Color fill=Enabled?(hover?FlatAppearance.MouseOverBackColor:BackColor):Theme.Card;
            using(var path=new System.Drawing.Drawing2D.GraphicsPath()){
                int right=Math.Max(8,Width-1),bottom=Math.Max(8,Height-1);path.AddArc(0,0,12,12,180,90);path.AddArc(right-12,0,12,12,270,90);path.AddArc(right-12,bottom-12,12,12,0,90);path.AddArc(0,bottom-12,12,12,90,90);path.CloseFigure();
                using(var brush=new SolidBrush(fill))g.FillPath(brush,path);if(FlatAppearance.BorderSize>0)using(var pen=new Pen(Theme.Line))g.DrawPath(pen,path);
            }
            var bounds=new Rectangle(12,0,Math.Max(1,Width-24),Height);var flags=TextFormatFlags.VerticalCenter|TextFormatFlags.EndEllipsis|(TextAlign==ContentAlignment.MiddleLeft?TextFormatFlags.Left:TextFormatFlags.HorizontalCenter);
            TextRenderer.DrawText(g,Text,Font,bounds,Enabled?ForeColor:Theme.Muted,flags);if(Focused)ControlPaint.DrawFocusRectangle(g,new Rectangle(4,4,Width-8,Height-8));
        }
    }
    sealed partial class Dashboard : Form {
        readonly string home;
        readonly Label title, description, notice;
        readonly Label[] values = new Label[4];
        readonly Button start, stop, restart, prepare;
        readonly CheckBox autostart;
        readonly System.Windows.Forms.Timer timer = new System.Windows.Forms.Timer();
        bool busy, refreshing, applying;
        bool ready, running;
        readonly List<Control> actions = new List<Control>();
        public Dashboard(string path,bool openStudio=false,bool openVisualizer=false) {
            home=path;
            Theme.Form(this,"APC40 Bridge",new Size(1160,780));
            MinimumSize=new Size(1040,740); MaximizeBox=true; FormBorderStyle=FormBorderStyle.Sizable;
            var root=new TableLayoutPanel { Dock=DockStyle.Fill, Padding=new Padding(26), ColumnCount=1, RowCount=8 };
            foreach (int h in new[]{76,122,90,58,52,58,66}) root.RowStyles.Add(new RowStyle(SizeType.Absolute,h));
            root.RowStyles.Add(new RowStyle(SizeType.Percent,100));
            Controls.Add(root);
            var heading=new TableLayoutPanel { Dock=DockStyle.Fill, ColumnCount=2, RowCount=1, Margin=Padding.Empty };
            heading.ColumnStyles.Add(new ColumnStyle(SizeType.Percent,75)); heading.ColumnStyles.Add(new ColumnStyle(SizeType.Percent,25));
            var words=new TableLayoutPanel { Dock=DockStyle.Fill, RowCount=2, Margin=Padding.Empty };
            words.RowStyles.Add(new RowStyle(SizeType.Percent,64)); words.RowStyles.Add(new RowStyle(SizeType.Percent,36));
            words.Controls.Add(Theme.Label("APC40 Bridge",25,Theme.Text),0,0);
            words.Controls.Add(Theme.Label("RESOLUME ARENA  /  CONTROL PANEL",9,Theme.Muted),0,1);
            heading.Controls.Add(words,0,0); heading.Controls.Add(new PadMark { Dock=DockStyle.Fill },1,0); root.Controls.Add(heading,0,0);
            var hero=new TableLayoutPanel { Dock=DockStyle.Fill, BackColor=Theme.Card, Padding=new Padding(20,12,20,12), RowCount=2, Margin=new Padding(0,12,0,10) };
            hero.RowStyles.Add(new RowStyle(SizeType.Percent,55)); hero.RowStyles.Add(new RowStyle(SizeType.Percent,45));
            title=Theme.Label("Checking status…",20,Theme.Text);
            description=Theme.Label("Please wait. The bridge can keep running in the background.",10,Theme.Muted);
            hero.Controls.Add(title,0,0); hero.Controls.Add(description,0,1); root.Controls.Add(hero,0,1);
            var cards=new TableLayoutPanel { Dock=DockStyle.Fill, ColumnCount=4, RowCount=1, Margin=new Padding(0,0,0,12) };
            string[] names={"CONTROLLER","RESOLUME ARENA","MIDI PORTS","SETUP"};
            for (int i=0;i<4;i++) {
                cards.ColumnStyles.Add(new ColumnStyle(SizeType.Percent,25));
                var card=new TableLayoutPanel { Dock=DockStyle.Fill, BackColor=Theme.Card, Padding=new Padding(12,8,8,8), RowCount=2, Margin=new Padding(0,0,i==3?0:8,0) };
                card.RowStyles.Add(new RowStyle(SizeType.Percent,45)); card.RowStyles.Add(new RowStyle(SizeType.Percent,55));
                card.Controls.Add(Theme.Label(names[i],8,Theme.Muted),0,0);
                values[i]=Theme.Label("—",11,Theme.Text);values[i].TextAlign=ContentAlignment.TopLeft; card.Controls.Add(values[i],0,1); cards.Controls.Add(card,i,0);
            }
            root.Controls.Add(cards,0,2);
            var row=new TableLayoutPanel { Dock=DockStyle.Fill, ColumnCount=4, RowCount=1, Margin=new Padding(0,2,0,10) };
            foreach(int percent in new[]{31,21,21,27}) row.ColumnStyles.Add(new ColumnStyle(SizeType.Percent,percent));
            start=Theme.Button("Start bridge",true); stop=Theme.Button("Stop",false); restart=Theme.Button("Restart",false); prepare=Theme.Button("Install / repair",false);
            row.Controls.Add(start,0,0);row.Controls.Add(stop,1,0);row.Controls.Add(restart,2,0);row.Controls.Add(prepare,3,0);
            actions.AddRange(new Control[]{start,stop,restart,prepare}); root.Controls.Add(row,0,3);
            start.Click+=async (s,e)=> { if (!ready) await Prepare(true); else await Perform("Starting bridge…","start"); };
            stop.Click+=async (s,e)=>await Perform("Stopping bridge…","stop");
            restart.Click+=async (s,e)=>await Operation("Restarting bridge…",()=> { Backend.Action(home,"stop"); return Backend.Action(home,"start"); });
            prepare.Click+=async (s,e)=>await Prepare(false);
            autostart=new CheckBox { Text="Start automatically when signing in to Windows", Dock=DockStyle.Fill, ForeColor=Theme.Text, Font=new Font("Segoe UI",10), Margin=new Padding(2,0,0,0), Cursor=Cursors.Hand };
            autostart.CheckedChanged+=async (s,e)=> { if (!applying) await Perform("Saving autostart settings…",autostart.Checked?"autostart-on":"autostart-off"); };
            actions.Add(autostart);root.Controls.Add(autostart,0,4);
            var more=new TableLayoutPanel { Dock=DockStyle.Fill, ColumnCount=6, RowCount=1, Margin=new Padding(0,4,0,8) };
            for(int i=0;i<6;i++)more.ColumnStyles.Add(new ColumnStyle(SizeType.Percent,100f/6));
            Button loop=Theme.Button("Open loopMIDI",false), settings=Theme.Button("Settings",false), logs=Theme.Button("View logs",false), shortcut=Theme.Button("Desktop shortcut",false), restore=Theme.Button("Restore Arena MIDI",false);
            Button studio=Theme.Button("Controller Studio",false);
            var visualizer=Theme.Button("Visualizer",true);
            more.ColumnCount=4;more.ColumnStyles.Clear();
            for(int i=0;i<4;i++)more.ColumnStyles.Add(new ColumnStyle(SizeType.Percent,25));

            more.Controls.Add(visualizer,3,0);
            visualizer.Font=new Font("Segoe UI",9);
            visualizer.Click+=(sender,e)=>ShowVisualizer();
            foreach(var b in new[]{studio,settings,logs,shortcut,loop,restore}) b.Font=new Font("Segoe UI",9);
            more.Controls.Add(loop,0,0);more.Controls.Add(shortcut,1,0);more.Controls.Add(restore,2,0);
            actions.AddRange(new Control[]{studio,settings,shortcut,restore});
            AddLocalTools(more);
            studio.Click+=(s,e)=>{try{ShowPage(()=>new ControllerEditor(home));}catch(Exception ex){ShowError(ex.Message);}};root.Controls.Add(more,0,5);
            settings.Click+=(s,e)=> { try { ShowPage(()=>new Settings(home)); }catch(Exception ex){ ShowError(ex.Message); } };
            logs.Click+=(s,e)=> { ShowPage(()=>new Logs(home)); };
            loop.Click+=(s,e)=> {
                try {
                    string[] candidates={Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.ProgramFilesX86), "Tobias Erichsen", "loopMIDI", "loopMIDI.exe"),Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.ProgramFiles), "Tobias Erichsen", "loopMIDI", "loopMIDI.exe")};
                    string exe=candidates.FirstOrDefault(File.Exists);
                    if(exe==null)throw new Exception("loopMIDI is not installed yet. Use Install / repair.");
                    Process.Start(new ProcessStartInfo(exe){UseShellExecute=true});
                }catch(Exception ex){ShowError(ex.Message);}
            };
            shortcut.Click+=async(s,e)=>await Perform("Creating shortcut…","shortcut");
            restore.Click+=async(s,e)=> {
                if(MessageBox.Show(this,"Restore Arena MIDI settings from the backup made before bridge setup? Arena must be closed. Later changes to these settings will be overwritten. The bridge will stop and autostart will be disabled.","Restore MIDI settings",MessageBoxButtons.YesNo,MessageBoxIcon.Question)==DialogResult.Yes)
                    await Perform("Restoring Arena settings…","restore");
            };
            notice=Theme.Label("Everything in one place. Closing this window does not stop the bridge.",9,Theme.Muted);
            notice.TextAlign=ContentAlignment.TopLeft; notice.Padding=new Padding(2,12,0,0);root.Controls.Add(notice,0,6);
            root.Controls.Add(Theme.Label(Backend.LastSession(home),9,Theme.Muted),0,7);
            FormClosing+=(s,e)=> { if(busy){e.Cancel=true;notice.Text="Please wait for the current operation to finish."; } };
            Shown+=async(s,e)=>await RefreshStatus();
            timer.Interval=5000;timer.Tick+=async(s,e)=>await RefreshStatus();timer.Start();
            FormClosed+=(s,e)=>timer.Dispose();
            BuildNavigation(root);
            FormClosing+=async(sender,e)=>{
                if(e.Cancel)return;
                var viewer=activePage as VisualizerPage;
                if(viewer!=null&&!viewer.ReadyToClose){e.Cancel=true;if(await viewer.PrepareCloseAsync())BeginInvoke(new Action(Close));}
                else if(!ClosePage())e.Cancel=true;
            };
            if(openVisualizer)Shown+=(sender,e)=>ShowVisualizer();
            else if(openStudio)Shown+=(sender,e)=>ShowPage(()=>new ControllerEditor(home));
        }
        partial void AddLocalTools(TableLayoutPanel tools);
        protected override void WndProc(ref Message message){
            if(message.Msg==Program.VisualizerMessage){if(WindowState==FormWindowState.Minimized)WindowState=FormWindowState.Normal;Show();Activate();ShowVisualizer();}
            base.WndProc(ref message);
        }
        void ShowVisualizer(){if(activePage is VisualizerPage){activePage.BringToFront();return;}ShowPage(()=>new VisualizerPage(home));}
        Panel pageHost;
        Control overview;
        Form activePage;
        bool switching,navigationBusy;
        void BuildNavigation(Control content){
            overview=content;Controls.Remove(content);
            var shell=new TableLayoutPanel{Dock=DockStyle.Fill,ColumnCount=2,RowCount=1,Margin=Padding.Empty};
            shell.ColumnStyles.Add(new ColumnStyle(SizeType.Absolute,190));shell.ColumnStyles.Add(new ColumnStyle(SizeType.Percent,100));
            var nav=new FlowLayoutPanel{Dock=DockStyle.Fill,FlowDirection=FlowDirection.TopDown,WrapContents=false,Padding=new Padding(16,26,10,16),BackColor=Theme.Card};
            nav.Controls.Add(new Label{Text="APC40 BRIDGE",AutoSize=false,Width=155,Height=56,ForeColor=Theme.Accent,Font=new Font("Segoe UI",12,FontStyle.Bold)});
            string[] names={"Overview","Controller Studio","Visualizer","Settings","Logs"};
            for(int i=0;i<names.Length;i++){
                int index=i;var button=Theme.Button(names[i],false);button.Dock=DockStyle.None;button.Width=155;button.Height=46;button.Margin=new Padding(0,0,0,8);button.TextAlign=ContentAlignment.MiddleLeft;
                button.Click+=(sender,e)=>{if(index==0)ShowOverview();else if(index==1)ShowPage(()=>new ControllerEditor(home));else if(index==2)ShowVisualizer();else if(index==3)ShowPage(()=>new Settings(home));else ShowPage(()=>new Logs(home));};nav.Controls.Add(button);
            }
            pageHost=new Panel{Dock=DockStyle.Fill};pageHost.Controls.Add(content);shell.Controls.Add(nav,0,0);shell.Controls.Add(pageHost,1,0);Controls.Add(shell);
        }
        bool ClosePage(){
            if(activePage==null)return true;
            var closing=activePage;switching=true;closing.Close();switching=false;
            if(!closing.IsDisposed)return false;activePage=null;return true;
        }
        async void ShowOverview(){
            if(navigationBusy||busy)return;navigationBusy=true;
            try{if(activePage is VisualizerPage&&!await ((VisualizerPage)activePage).PrepareCloseAsync())return;if(!ClosePage())return;overview.Show();overview.BringToFront();timer.Start();}
            catch(Exception ex){ShowError(ex.Message);}finally{navigationBusy=false;}
        }
        async void ShowPage(Func<Form> create){
            if(navigationBusy||busy)return;navigationBusy=true;
            try{
                if(activePage is VisualizerPage&&!await ((VisualizerPage)activePage).PrepareCloseAsync())return;
                if(!ClosePage())return;
                activePage=create();activePage.MinimumSize=Size.Empty;activePage.MaximumSize=Size.Empty;activePage.TopLevel=false;activePage.FormBorderStyle=FormBorderStyle.None;activePage.Dock=DockStyle.Fill;
                activePage.FormClosed+=(sender,e)=>{if(!switching){if(sender is Settings&&((Form)sender).DialogResult==DialogResult.OK)notice.Text="Settings saved. Restart the bridge to apply MIDI settings.";activePage=null;overview.Show();overview.BringToFront();timer.Start();}};
                overview.Hide();timer.Stop();pageHost.Controls.Add(activePage);activePage.Show();activePage.BringToFront();if(!(activePage is VisualizerPage))AnimatePage(activePage);
            }catch(Exception ex){ShowError(ex.Message);}finally{navigationBusy=false;}
        }
        void AnimatePage(Form page){
            if(!SystemInformation.IsMenuAnimationEnabled)return;
            page.Dock=DockStyle.None;page.Anchor=AnchorStyles.Top|AnchorStyles.Bottom|AnchorStyles.Left|AnchorStyles.Right;
            var watch=Stopwatch.StartNew();var motion=new System.Windows.Forms.Timer{Interval=16};
            page.Disposed+=(sender,e)=>motion.Dispose();
            motion.Tick+=(sender,e)=>{if(page.IsDisposed){motion.Dispose();return;}double amount=Math.Min(1,watch.Elapsed.TotalMilliseconds/140.0);int offset=(int)(16*(1-amount)*(1-amount));page.SetBounds(offset,0,Math.Max(1,pageHost.Width-offset),pageHost.Height);if(amount>=1){page.Dock=DockStyle.Fill;page.Invalidate(true);page.Refresh();motion.Dispose();}};motion.Start();
        }
        async Task RefreshStatus() {
            if (busy || refreshing || IsDisposed || !Enabled) return;
            refreshing=true;
            try {
                var status=await Task.Run(()=>Backend.Action(home,"status"));
                if(IsDisposed || busy)return;
                ready=Backend.Flag(status,"python_ready")&&Backend.Flag(status,"dependencies_ready")&&Backend.Flag(status,"virtual_ready")&&Backend.Flag(status,"preferences_ready");
                running=Backend.Flag(status,"bridge_running");
                bool arena=Backend.Flag(status,"arena_running"), apc=Backend.Flag(status,"apc_ready"), ports=Backend.Flag(status,"virtual_ready");
                SetValue(0,apc?"Connected":"Disconnected",apc);
                SetValue(1,arena?"Running":"Closed",arena);
                SetValue(2,ports?"Ready":"Ports missing",ports);
                SetValue(3,ready?"Ready":"Setup needed",ready);
                title.Text=running?(arena?"Bridge running":"Waiting for Arena"):(ready?"Ready to start":"Welcome. Let’s set things up.");
                title.ForeColor=running?Theme.Accent:Theme.Text;
                description.Text=!ready?"Setup will find the required components and guide you through configuration.":!ports?"Create APC VIRT A and APC VIRT B in loopMIDI.":!apc?"Connect your APC40 mkII via USB. The bridge will wait for it.":running?"The bridge is running in the background. You can close this window.":"Start the bridge, then open your composition in Arena.";
                start.Text=ready?"Start bridge":"Prepare and start";
                start.Enabled=!running;stop.Enabled=running;restart.Enabled=running;
                applying=true;autostart.Checked=Backend.Flag(status,"autostart");applying=false;
            } catch(Exception ex) {
                title.Text="Could not read status";description.Text="Try Install / repair or open the logs.";
                notice.Text=ex.Message;
            } finally { refreshing=false; }
        }
        void SetValue(int i,string text,bool good){values[i].Text=text;values[i].ForeColor=good?Theme.Accent:Theme.Muted;}
        void ShowError(string text){notice.Text=text;MessageBox.Show(this,text,"APC40 Bridge",MessageBoxButtons.OK,MessageBoxIcon.Warning);}
        async Task Perform(string label,string action){await Operation(label,()=>Backend.Action(home,action));}
        async Task Prepare(bool thenStart) {
            await Operation("Preparing setup. Follow progress in the Setup log…",()=>{
                Backend.Run(home,"setup.ps1","-NoPopup -PrepareOnly",1200000);
                if(thenStart)return Backend.Action(home,"start");
                return new Dictionary<string,object>{{"message","Setup complete. You can start the bridge."}};
            });
        }
        async Task Operation(string label,Func<Dictionary<string,object>> action) {
            if(busy)return;
            busy=true;foreach(Control c in actions)c.Enabled=false;notice.Text=label;UseWaitCursor=true;
            try {
                var result=await Task.Run(action);
                notice.Text=result.ContainsKey("message")?Convert.ToString(result["message"]):"Done.";
            } catch(Exception ex){ShowError(ex.Message);}
            finally {busy=false;UseWaitCursor=false;foreach(Control c in actions)c.Enabled=true;}
            await RefreshStatus();
        }
    }
    sealed class PadMark : Control {
        protected override void OnPaint(PaintEventArgs e) {
            Color[] colors={Color.FromArgb(245,105,112),Color.FromArgb(244,169,95),Color.FromArgb(229,220,104),Theme.Accent,Color.FromArgb(90,201,220),Color.FromArgb(108,161,246),Color.FromArgb(159,130,246),Color.FromArgb(216,129,223)};
            int size=10,gap=5;int left=Math.Max(4,Width-8*(size+gap));
            for(int row=0;row<4;row++)for(int col=0;col<8;col++)using(var brush=new SolidBrush(row==0?colors[col]:Color.FromArgb(46,57,70)))e.Graphics.FillRectangle(brush,left+col*(size+gap),10+row*(size+gap),size,size);
        }
    }
    sealed class ValueSlider : Control {
        readonly decimal minimum,maximum;readonly int digits;decimal current;bool dragging;
        public event EventHandler ValueChanged;
        public decimal Value{get{return current;}set{decimal next=Math.Round(Math.Max(minimum,Math.Min(maximum,value)),digits);if(next==current)return;current=next;Invalidate();if(ValueChanged!=null)ValueChanged(this,EventArgs.Empty);}}
        public ValueSlider(decimal min,decimal max,decimal value,int precision){minimum=min;maximum=max;digits=precision;current=Math.Max(min,Math.Min(max,value));Dock=DockStyle.Fill;TabStop=true;Cursor=Cursors.Hand;SetStyle(ControlStyles.UserPaint|ControlStyles.AllPaintingInWmPaint|ControlStyles.OptimizedDoubleBuffer|ControlStyles.Selectable|ControlStyles.ResizeRedraw,true);Height=42;}
        void Pick(int x){Value=minimum+(maximum-minimum)*(decimal)Math.Max(0,Math.Min(1,(x-10.0)/Math.Max(1,Width-110)));}
        protected override void OnMouseDown(MouseEventArgs e){base.OnMouseDown(e);Focus();dragging=true;Capture=true;Pick(e.X);}
        protected override void OnMouseMove(MouseEventArgs e){base.OnMouseMove(e);if(dragging)Pick(e.X);}
        protected override void OnMouseUp(MouseEventArgs e){base.OnMouseUp(e);dragging=false;Capture=false;}
        protected override bool IsInputKey(Keys key){return key==Keys.Left||key==Keys.Right||key==Keys.Home||key==Keys.End||base.IsInputKey(key);}
        protected override void OnKeyDown(KeyEventArgs e){base.OnKeyDown(e);decimal step=digits==0?1m:(maximum-minimum)/1000m;if(e.KeyCode==Keys.Left)Value-=step;if(e.KeyCode==Keys.Right)Value+=step;if(e.KeyCode==Keys.Home)Value=minimum;if(e.KeyCode==Keys.End)Value=maximum;}
        protected override void OnPaint(PaintEventArgs e){base.OnPaint(e);var g=e.Graphics;g.Clear(Parent==null?Theme.Bg:Parent.BackColor);g.SmoothingMode=System.Drawing.Drawing2D.SmoothingMode.AntiAlias;float end=Math.Max(11,Width-100),y=Height/2f,x=10+(end-10)*(float)((current-minimum)/(maximum-minimum));using(var track=new Pen(Theme.Line,4))g.DrawLine(track,10,y,end,y);using(var active=new Pen(Theme.Accent,4))g.DrawLine(active,10,y,x,y);using(var fill=new SolidBrush(Theme.Accent))g.FillEllipse(fill,x-6,y-6,12,12);TextRenderer.DrawText(g,current.ToString(digits==0?"0":"0."+new string('0',digits),System.Globalization.CultureInfo.InvariantCulture),Font,new Rectangle((int)end+10,0,90,Height),Theme.Text,TextFormatFlags.VerticalCenter|TextFormatFlags.Left);if(Focused)ControlPaint.DrawFocusRectangle(g,ClientRectangle);}
    }
    sealed class FrequencySlider : UserControl {
        readonly ValueSlider slider;
        readonly Label caption;
        public event EventHandler ValueChanged;
        public decimal Value {
            get { return slider.Value; }
            set { slider.Value=value; }
        }
        public FrequencySlider(decimal minimum,decimal maximum,decimal value) {
            Dock=DockStyle.Fill;Margin=new Padding(0,2,0,2);
            var layout=new TableLayoutPanel{Dock=DockStyle.Fill,ColumnCount=1,RowCount=2,Margin=Padding.Empty};
            layout.RowStyles.Add(new RowStyle(SizeType.Percent,100));layout.RowStyles.Add(new RowStyle(SizeType.Absolute,19));Controls.Add(layout);
            slider=new ValueSlider(minimum,maximum,value,1){AccessibleName="Blink speed in Hz"};
            caption=Theme.Label("",9,Theme.Muted);caption.TextAlign=ContentAlignment.MiddleCenter;
            layout.Controls.Add(slider,0,0);layout.Controls.Add(caption,0,1);
            slider.ValueChanged+=(sender,e)=>{UpdateCaption();if(ValueChanged!=null)ValueChanged(this,EventArgs.Empty);};
            UpdateCaption();
        }
        void UpdateCaption(){caption.Text="Slow   "+Value.ToString("0.0",System.Globalization.CultureInfo.InvariantCulture)+" Hz   Fast";}
    }
    sealed class Settings : Form {
        readonly string file;
        readonly Dictionary<string,object> cfg;
        readonly TextBox apc,to,from;
        readonly ValueSlider hue;
        readonly FrequencySlider blink;
        readonly CheckBox feedback,lit,speedRings;
        public Settings(string home) {
            file=Path.Combine(home,"config.json");
            cfg=Backend.Json.Deserialize<Dictionary<string,object>>(File.ReadAllText(file,Encoding.UTF8));
            Theme.Form(this,"Bridge settings",new Size(650,604));FormBorderStyle=FormBorderStyle.FixedDialog;MaximizeBox=false;MinimizeBox=false;
            var root=new TableLayoutPanel{Dock=DockStyle.Fill,Padding=new Padding(24),ColumnCount=2,RowCount=12};
            root.ColumnStyles.Add(new ColumnStyle(SizeType.Absolute,190));root.ColumnStyles.Add(new ColumnStyle(SizeType.Percent,100));Controls.Add(root);
            for(int i=0;i<11;i++)root.RowStyles.Add(new RowStyle(SizeType.Absolute,i==4?64:38));
            root.RowStyles.Add(new RowStyle(SizeType.Absolute,52));root.RowCount=13;root.RowStyles.Add(new RowStyle(SizeType.Percent,100));
            apc=Theme.Input(Get("apc_port_match","APC40"));to=Theme.Input(Get("to_resolume_port","APC VIRT A"));from=Theme.Input(Get("from_resolume_port","APC VIRT B"));
            hue=Number(Get("hue_max","0.63871"),0.001m,1m,5);blink=new FrequencySlider(.5m,10m,Math.Max(.5m,Math.Min(10m,decimal.Parse(Get("blink_hz","3"),System.Globalization.CultureInfo.InvariantCulture))));
            feedback=new CheckBox{Text="Sync changes from Arena",Checked=GetBool("sync_resolume_feedback"),Dock=DockStyle.Fill,ForeColor=Theme.Text};
            lit=new CheckBox{Text="Keep utility buttons lit",Checked=GetBool("always_lit"),Dock=DockStyle.Fill,ForeColor=Theme.Text};
            speedRings=new CheckBox{Text="Blink speed buttons; press to reset to 1x",Checked=GetBool("speed_button_pulse"),Dock=DockStyle.Fill,ForeColor=Theme.Text};
            string[] labels={"Controller name","Port to Arena","Port from Arena","Hue upper limit","Utility blink speed","Feedback","Lighting","Speed buttons"};
            Control[] inputs={apc,to,from,hue,blink,feedback,lit,speedRings};
            for(int i=0;i<labels.Length;i++){root.Controls.Add(Theme.Label(labels[i],10,Theme.Muted),0,i);root.Controls.Add(inputs[i],1,i);}
            var note=Theme.Label(Backend.LastSession(home),9,Theme.Muted);root.Controls.Add(note,0,8);root.SetColumnSpan(note,2);
            var crossfade=new CheckBox{Text="Crossfader: A = GLOBAL, B = four groups (show mapping)",Checked=GetBool("global_crossfade"),Dock=DockStyle.Fill,ForeColor=Theme.Text};root.Controls.Add(crossfade,0,9);root.SetColumnSpan(crossfade,2);
            string previewDir=Path.Combine(home,"visualizer");
            var visual=new CheckBox{Text="Open LED visualizer with Arena (SpoutCam)",Checked=GetBool("led_visualizer"),Enabled=File.Exists(Path.Combine(previewDir,"preview.html")),Dock=DockStyle.Fill,ForeColor=Theme.Text};
            root.Controls.Add(visual,0,10);root.SetColumnSpan(visual,2);
            var save=Theme.Button("Save settings",true);root.Controls.Add(save,1,11);AcceptButton=save;
            save.Click+=(s,e)=>{
                if(string.IsNullOrWhiteSpace(apc.Text)||string.IsNullOrWhiteSpace(to.Text)||string.IsNullOrWhiteSpace(from.Text)||to.Text.Trim().Equals(from.Text.Trim(),StringComparison.OrdinalIgnoreCase)){
                    MessageBox.Show(this,"Enter the port names. Input and output virtual ports must be different.","Settings",MessageBoxButtons.OK,MessageBoxIcon.Information);return;
                }
                try{
                    cfg["apc_port_match"]=apc.Text.Trim();cfg["to_resolume_port"]=to.Text.Trim();cfg["from_resolume_port"]=from.Text.Trim();
                    if(visual.Checked&&!GetBool("led_visualizer")&&MessageBox.Show(this,"Install and register SpoutCam? If needed, the camera is downloaded from its publisher and verified. Windows will ask for administrator permission. Choose No if it is already registered.","LED visualizer",MessageBoxButtons.YesNo)==DialogResult.Yes)
                        Process.Start(new ProcessStartInfo(Path.Combine(home,"runtime","pythonw.exe"),"\""+Path.Combine(previewDir,"install_camera.py")+"\""){WorkingDirectory=previewDir,UseShellExecute=false,CreateNoWindow=true});
                    cfg["led_visualizer"]=visual.Checked;
                    cfg["global_crossfade"]=crossfade.Checked;cfg["hue_max"]=hue.Value;cfg["blink_hz"]=blink.Value;cfg["sync_resolume_feedback"]=feedback.Checked;cfg["always_lit"]=lit.Checked;cfg["speed_button_pulse"]=speedRings.Checked;cfg["speed_ring_animation"]=false;
                    string backup=file+".before-settings-"+DateTime.Now.ToString("yyyyMMdd-HHmmss-fff")+".bak";
                    string temp=file+".settings.tmp";
                    File.WriteAllText(temp,Backend.Json.Serialize(cfg),new UTF8Encoding(false));
                    File.Replace(temp,file,backup);
                    DialogResult=DialogResult.OK;Close();
                }catch(Exception ex){MessageBox.Show(this,ex.Message,"Could not save settings");}
            };
        }
        string Get(string key,string fallback){return cfg.ContainsKey(key)?Convert.ToString(cfg[key],System.Globalization.CultureInfo.InvariantCulture):fallback;}
        bool GetBool(string key){return cfg.ContainsKey(key)&&cfg[key] is bool&&(bool)cfg[key];}
        ValueSlider Number(string value,decimal min,decimal max,int digits){
            decimal number;if(!decimal.TryParse(value,System.Globalization.NumberStyles.Float,System.Globalization.CultureInfo.InvariantCulture,out number))throw new Exception("Invalid numeric setting.");
            return new ValueSlider(min,max,number,digits);
        }
    }
    sealed class Logs : Form {
        readonly string home;
        readonly ComboBox source;
        readonly TextBox text;
        readonly System.Windows.Forms.Timer timer=new System.Windows.Forms.Timer();
        string[] names={"bridge.log","setup.log","management.log"};
        public Logs(string path){
            home=path;Theme.Form(this,"Bridge logs",new Size(850,500));MinimumSize=new Size(650,400);
            var root=new TableLayoutPanel{Dock=DockStyle.Fill,Padding=new Padding(20),ColumnCount=1,RowCount=2};
            root.RowStyles.Add(new RowStyle(SizeType.Absolute,44));root.RowStyles.Add(new RowStyle(SizeType.Percent,100));Controls.Add(root);
            source=new ComboBox{Dock=DockStyle.Left,Width=240,DropDownStyle=ComboBoxStyle.DropDownList,BackColor=Theme.Card,ForeColor=Theme.Text};
            source.Items.AddRange(new object[]{"Bridge runtime","Setup","App management"});source.SelectedIndex=0;root.Controls.Add(source,0,0);
            text=new TextBox{Dock=DockStyle.Fill,Multiline=true,ReadOnly=true,ScrollBars=ScrollBars.Both,WordWrap=false,BackColor=Theme.Card,ForeColor=Theme.Text,BorderStyle=BorderStyle.None,Font=new Font("Consolas",9)};
            root.Controls.Add(text,0,1);source.SelectedIndexChanged+=(s,e)=>RefreshLog();timer.Interval=1500;timer.Tick+=(s,e)=>RefreshLog();timer.Start();RefreshLog();Shown+=(s,e)=>{text.SelectionStart=text.Text.Length;text.ScrollToCaret();};FormClosed+=(s,e)=>timer.Dispose();
        }
        void RefreshLog(){try{string value=Backend.ReadLog(Path.Combine(home,names[source.SelectedIndex]));if(text.Text!=value){text.Text=value;text.SelectionStart=text.Text.Length;text.ScrollToCaret();}}catch(Exception ex){text.Text=ex.Message;}}
    }
}
