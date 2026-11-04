using System;
using System.IO;
using System.IO.Compression;
using System.Linq;
using System.Text;
using System.Drawing;
using System.Diagnostics;
using System.Collections.Generic;
using System.Security.Cryptography;
using System.Net;
using System.Threading;
using System.Threading.Tasks;
using System.Windows.Forms;
using System.Web.Script.Serialization;
using Microsoft.Win32;

[assembly: System.Reflection.AssemblyTitle("APC40 Bridge Setup")]
[assembly: System.Reflection.AssemblyProduct("APC40 Bridge")]
[assembly: System.Reflection.AssemblyCompany("Technical223")]
[assembly: System.Reflection.AssemblyVersion("1.5.2.0")]
[assembly: System.Reflection.AssemblyFileVersion("1.5.2.0")]

namespace ApcSetup {
 static class Package {
  internal const string LoopUrl="https://www.tobias-erichsen.de/wp-content/uploads/2020/01/loopMIDISetup_1_0_16_27.zip";
  internal const string LoopHash="86db060b586b57dbeeaab32412602a9dd7f9e4298ab7586e667b7e7dbcf60ed6";
  internal const string UninstallKey=@"Software\Microsoft\Windows\CurrentVersion\Uninstall\APC40Bridge";
  internal static string Hash(string path){using(var sha=SHA256.Create())using(var stream=File.OpenRead(path))return BitConverter.ToString(sha.ComputeHash(stream)).Replace("-","").ToLowerInvariant();}
  internal static string Child(string root,string relative){
   string target=Path.GetFullPath(Path.Combine(root,relative.Replace('/',Path.DirectorySeparatorChar)));
   string prefix=Path.GetFullPath(root).TrimEnd(Path.DirectorySeparatorChar)+Path.DirectorySeparatorChar;
   if(!target.StartsWith(prefix,StringComparison.OrdinalIgnoreCase))throw new IOException("The package contains an invalid path.");
   return target;
  }
  internal static void Extract(string destination){
   Directory.CreateDirectory(destination);
   using(var stream=typeof(Package).Assembly.GetManifestResourceStream("ApcBridge.Payload.zip")){
    if(stream==null)throw new IOException("The embedded app package is missing.");
    using(var zip=new ZipArchive(stream,ZipArchiveMode.Read)){
     foreach(var item in zip.Entries){
      if(item.FullName.EndsWith("/"))continue;
      string path=Child(destination,item.FullName);Directory.CreateDirectory(Path.GetDirectoryName(path));
      using(var input=item.Open())using(var output=File.Create(path))input.CopyTo(output);
     }
    }
   }
   var data=new JavaScriptSerializer().Deserialize<Dictionary<string,object>>(File.ReadAllText(Path.Combine(destination,"package-manifest.json")));
   foreach(var item in (System.Collections.IEnumerable)data["files"]){
    var entry=(Dictionary<string,object>)item;
    if(Hash(Child(destination,Convert.ToString(entry["path"])))!=Convert.ToString(entry["sha256"]))throw new IOException("The app package failed its integrity check.");
   }
  }
  internal static bool AppOpen(string folder){
   string key;using(var sha=SHA256.Create())key=Convert.ToBase64String(sha.ComputeHash(Encoding.UTF8.GetBytes(folder.ToLowerInvariant()))).Replace("/","_");
   try{using(var mutex=Mutex.OpenExisting("Local\\APC40ControlPanel_"+key))return true;}catch(WaitHandleCannotBeOpenedException){return false;}
  }
  internal static string LoopExe(){return new[]{Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.ProgramFilesX86),"Tobias Erichsen","loopMIDI","loopMIDI.exe"),Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.ProgramFiles),"Tobias Erichsen","loopMIDI","loopMIDI.exe")}.FirstOrDefault(File.Exists);}
  internal static int RunScript(string folder,string script,string args,int minutes){
   var info=new ProcessStartInfo(Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.System),@"WindowsPowerShell\v1.0\powershell.exe"),"-NoProfile -NonInteractive -ExecutionPolicy Bypass -File \""+Path.Combine(folder,script)+"\" "+args){WorkingDirectory=folder,UseShellExecute=false,CreateNoWindow=true,RedirectStandardOutput=true,RedirectStandardError=true};
   using(var p=Process.Start(info)){
    var output=p.StandardOutput.ReadToEndAsync();var error=p.StandardError.ReadToEndAsync();
    if(!p.WaitForExit(minutes*60000)){try{p.Kill();p.WaitForExit();}catch{}throw new IOException("Preparation timed out. Open the app's Setup log for details.");}
    File.AppendAllText(Path.Combine(folder,"installer.log"),output.Result+"\n"+error.Result);return p.ExitCode;
   }
  }
  internal static void PreparePorts(string folder){
   string a="APC VIRT A",b="APC VIRT B",config=Path.Combine(folder,"config.json");
   if(File.Exists(config)){var cfg=new JavaScriptSerializer().Deserialize<Dictionary<string,object>>(File.ReadAllText(config));if(cfg.ContainsKey("to_resolume_port"))a=Convert.ToString(cfg["to_resolume_port"]);if(cfg.ContainsKey("from_resolume_port"))b=Convert.ToString(cfg["from_resolume_port"]);}
   using(var key=Registry.CurrentUser.CreateSubKey(@"Software\Tobias Erichsen\loopMIDI\Ports")){foreach(string name in new[]{a,b})if(!string.IsNullOrWhiteSpace(name)&&key.GetValue(name)==null)key.SetValue(name,1,RegistryValueKind.DWord);}
  }
  internal static void CopyFiles(string stage,string target){
   Directory.CreateDirectory(target);string backup=Path.Combine(target,"backups","before-install-"+DateTime.Now.ToString("yyyyMMdd-HHmmss-fff"));Directory.CreateDirectory(backup);
   foreach(string name in new[]{"config.json","state.json","APC40 Bridge.exe","apc_bridge.py","runtime.ps1","setup.ps1","manage.ps1"})if(File.Exists(Path.Combine(target,name)))File.Copy(Path.Combine(target,name),Path.Combine(backup,name),false);
   foreach(string path in Directory.GetFiles(stage,"*",SearchOption.AllDirectories).OrderBy(x=>Path.GetFileName(x)=="APC40 Bridge.exe"?1:0)){
    string relative=path.Substring(stage.Length).TrimStart(Path.DirectorySeparatorChar),dest=Child(target,relative);
    if(File.Exists(dest)&&(relative=="config.json"||relative.StartsWith("profiles"+Path.DirectorySeparatorChar,StringComparison.OrdinalIgnoreCase)))continue;
    Directory.CreateDirectory(Path.GetDirectoryName(dest));File.Copy(path,dest,true);
   }
  }
  internal static void Register(string target){
   string exe=Path.Combine(target,"APC40 Bridge.exe");
   dynamic shell=Activator.CreateInstance(Type.GetTypeFromProgID("WScript.Shell"));
   try{foreach(string path in new[]{Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.DesktopDirectory),"APC40 Bridge.lnk"),Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.Programs),"APC40 Bridge.lnk")}){dynamic link=shell.CreateShortcut(path);try{link.TargetPath=exe;link.WorkingDirectory=target;link.IconLocation=exe+",0";link.Save();}finally{System.Runtime.InteropServices.Marshal.FinalReleaseComObject(link);}}}finally{System.Runtime.InteropServices.Marshal.FinalReleaseComObject(shell);}
   using(var key=Registry.CurrentUser.CreateSubKey(UninstallKey)){key.SetValue("DisplayName","APC40 Bridge");key.SetValue("DisplayVersion","1.3.0");key.SetValue("Publisher","Technical223");key.SetValue("InstallLocation",target);key.SetValue("DisplayIcon",exe);key.SetValue("UninstallString","\""+Path.Combine(target,"Uninstall.exe")+"\" --uninstall");key.SetValue("NoModify",1,RegistryValueKind.DWord);key.SetValue("NoRepair",1,RegistryValueKind.DWord);}
  }
  internal static void CleanTemp(string path){string full=Path.GetFullPath(path),root=Path.GetFullPath(Path.GetTempPath());if(full.StartsWith(root,StringComparison.OrdinalIgnoreCase)&&Path.GetFileName(full).StartsWith("APC40-Setup-"))try{Directory.Delete(full,true);}catch{}}
  internal static void Uninstall(){
   string target=AppDomain.CurrentDomain.BaseDirectory.TrimEnd(Path.DirectorySeparatorChar);
   if(AppOpen(target)){MessageBox.Show("Close APC40 Bridge before uninstalling.","APC40 Bridge");return;}
   if(MessageBox.Show("Remove APC40 Bridge? Your configuration, profiles, backups and logs will be kept. loopMIDI will remain installed.","Uninstall APC40 Bridge",MessageBoxButtons.YesNo,MessageBoxIcon.Question)!=DialogResult.Yes)return;
   if(RunScript(target,"manage.ps1","-Action stop",1)!=0)throw new IOException("Could not stop the bridge. Open its logs before uninstalling.");
   var data=new JavaScriptSerializer().Deserialize<Dictionary<string,object>>(File.ReadAllText(Path.Combine(target,"package-manifest.json")));
   foreach(var item in (System.Collections.IEnumerable)data["files"]){string rel=Convert.ToString(((Dictionary<string,object>)item)["path"]);if(rel=="config.json"||rel=="Uninstall.exe"||rel.StartsWith("profiles/"))continue;string file=Child(target,rel);if(File.Exists(file))File.Delete(file);}
   foreach(string shortcut in new[]{Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.DesktopDirectory),"APC40 Bridge.lnk"),Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.Programs),"APC40 Bridge.lnk"),Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.Startup),"APC40 Bridge.lnk")}){
    if(!File.Exists(shortcut))continue;
    dynamic shell=Activator.CreateInstance(Type.GetTypeFromProgID("WScript.Shell"));dynamic link=null;
    try{link=shell.CreateShortcut(shortcut);if(Convert.ToString(link.TargetPath).Equals(Path.Combine(target,"APC40 Bridge.exe"),StringComparison.OrdinalIgnoreCase))File.Delete(shortcut);}
    finally{if(link!=null)System.Runtime.InteropServices.Marshal.FinalReleaseComObject(link);System.Runtime.InteropServices.Marshal.FinalReleaseComObject(shell);}
   }
   Registry.CurrentUser.DeleteSubKey(UninstallKey,false);MessageBox.Show("The app was removed. Your user data and the small uninstaller were kept in the installation folder.","APC40 Bridge");
  }
 }

 sealed class SetupForm:Form {
  readonly Label state;readonly ProgressBar progress;readonly Button install;readonly CheckBox launch;
  readonly string target=Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),"Programs","APC40 Bridge");
  bool busy;
  public SetupForm(){
   Text="Install APC40 Bridge";ClientSize=new Size(860,580);StartPosition=FormStartPosition.CenterScreen;FormBorderStyle=FormBorderStyle.FixedDialog;MaximizeBox=false;
   BackColor=Color.FromArgb(18,22,28);ForeColor=Color.FromArgb(238,243,249);Font=new Font("Segoe UI",10);
   var shell=new TableLayoutPanel{Dock=DockStyle.Fill,ColumnCount=2,RowCount=1,Margin=Padding.Empty};shell.ColumnStyles.Add(new ColumnStyle(SizeType.Absolute,224));shell.ColumnStyles.Add(new ColumnStyle(SizeType.Percent,100));Controls.Add(shell);
   var sidebar=new TableLayoutPanel{Dock=DockStyle.Fill,Padding=new Padding(24,34,16,24),BackColor=Color.FromArgb(25,32,43),ColumnCount=1,RowCount=4};sidebar.RowStyles.Add(new RowStyle(SizeType.Absolute,78));sidebar.RowStyles.Add(new RowStyle(SizeType.Absolute,64));sidebar.RowStyles.Add(new RowStyle(SizeType.Absolute,160));sidebar.RowStyles.Add(new RowStyle(SizeType.Percent,100));
   sidebar.Controls.Add(Label("APC40\nBRIDGE",22,Color.FromArgb(105,229,181)),0,0);sidebar.Controls.Add(Label("WINDOWS SETUP",10,Color.FromArgb(154,167,184)),0,1);sidebar.Controls.Add(Label("01  Application\n\n02  MIDI routing\n\n03  Ready to connect",11,ForeColor),0,2);sidebar.Controls.Add(Label("Your controller.\nYour workflow.",12,Color.FromArgb(154,167,184)),0,3);shell.Controls.Add(sidebar,0,0);
   var root=new TableLayoutPanel{Dock=DockStyle.Fill,Padding=new Padding(32),ColumnCount=1,RowCount=7};shell.Controls.Add(root,1,0);
   foreach(int h in new[]{60,46,106,66,26,52,58})root.RowStyles.Add(new RowStyle(SizeType.Absolute,h));
   root.Controls.Add(Label("Ready for your controller",23,ForeColor),0,0);
   root.Controls.Add(Label("APC40 mkII + Resolume Arena",12,Color.FromArgb(154,167,184)),0,1);
   root.Controls.Add(Label("Install the app, Controller Studio and MIDI feedback.\nEverything runs locally on your computer.\nSetup prepares MIDI ports and guides you through loopMIDI when needed.",10,ForeColor),0,2);
   root.Controls.Add(Label("Install for this Windows account\n"+target,9,Color.FromArgb(154,167,184)),0,3);
   progress=new ProgressBar{Dock=DockStyle.Fill,Style=ProgressBarStyle.Continuous};root.Controls.Add(progress,0,4);
   state=Label("Your existing settings and profiles will be preserved.",9,Color.FromArgb(154,167,184));root.Controls.Add(state,0,5);
   var bottom=new TableLayoutPanel{Dock=DockStyle.Fill,ColumnCount=2};bottom.ColumnStyles.Add(new ColumnStyle(SizeType.Percent,60));bottom.ColumnStyles.Add(new ColumnStyle(SizeType.Percent,40));
   launch=new CheckBox{Text="Open APC40 Bridge",Checked=true,Dock=DockStyle.Fill,ForeColor=ForeColor};bottom.Controls.Add(launch,0,0);
   install=new Button{Text="Install APC40 Bridge",Font=new Font("Segoe UI",11,FontStyle.Regular),Cursor=Cursors.Hand,Dock=DockStyle.Fill,FlatStyle=FlatStyle.Flat,BackColor=Color.FromArgb(105,229,181),ForeColor=BackColor};bottom.Controls.Add(install,1,0);root.Controls.Add(bottom,0,6);
   install.Click+=async(s,e)=>await Install();
   FormClosing+=(s,e)=>{if(busy){e.Cancel=true;state.Text="Please wait for installation to finish."; }};
  }
  static Label Label(string text,int size,Color color){return new Label{Text=text,Dock=DockStyle.Fill,ForeColor=color,Font=new Font("Segoe UI",Math.Max(10,size)),TextAlign=ContentAlignment.MiddleLeft};}
  void Update(string text,int value){if(IsDisposed)return;BeginInvoke(new Action(()=>{state.Text=text;progress.Value=value;}));}
  async Task Install(){
   if(Package.AppOpen(target)){MessageBox.Show(this,"Close APC40 Bridge, then click Install again.","App is open");return;}
   busy=true;install.Enabled=false;string stage=Path.Combine(Path.GetTempPath(),"APC40-Setup-"+Guid.NewGuid().ToString("N"));
   try{
    await Task.Run(()=>{
     Update("Checking the app package…",10);Package.Extract(stage);
     Package.PreparePorts(target);
     if(Package.LoopExe()==null){
      string local=Path.Combine(AppDomain.CurrentDomain.BaseDirectory,"dependencies","loopMIDISetup.exe");
      string vendor=Path.Combine(stage,"loopMIDISetup.exe");
      if(File.Exists(local)){File.Copy(local,vendor);Update("Using the local loopMIDI installer…",25);}
      else{
       Update("Downloading loopMIDI from its publisher…",20);ServicePointManager.SecurityProtocol=SecurityProtocolType.Tls12;
       string archive=Path.Combine(stage,"loopMIDI.zip");
       using(var client=new WebClient())client.DownloadFile(Package.LoopUrl,archive);
       using(var zip=ZipFile.OpenRead(archive)){var entry=zip.GetEntry("loopMIDISetup.exe");if(entry==null)throw new IOException("The loopMIDI download has an unexpected format.");entry.ExtractToFile(vendor);}
       File.Delete(archive);
      }
      if(Package.Hash(vendor)!=Package.LoopHash)throw new IOException("The loopMIDI installer failed its integrity check.");
      Update("Complete the loopMIDI license and Windows permission prompts.",35);
      using(var vendorProcess=Process.Start(new ProcessStartInfo(vendor){UseShellExecute=true}))vendorProcess.WaitForExit();
      if(Package.LoopExe()==null)throw new IOException("loopMIDI was not installed. You can run this setup again.");
      File.Delete(vendor);
     }
     Update("Installing the app and bundled runtime…",55);
     if(File.Exists(Path.Combine(target,"manage.ps1"))&&Package.RunScript(target,"manage.ps1","-Action stop",1)!=0)throw new IOException("Could not stop the existing bridge. Close it from the dashboard and try again.");
     Package.CopyFiles(stage,target);Package.Register(target);
     Update("Preparing MIDI ports and Arena settings…",80);
     int result=Package.RunScript(target,"setup.ps1","-Offline -NoPopup -PrepareOnly",3);
     Update(result==0?"Installed. Your app is ready.":"Installed. Open the app's Setup log to complete Arena preparation.",100);
    });
    if(launch.Checked)Process.Start(new ProcessStartInfo(Path.Combine(target,"APC40 Bridge.exe")){UseShellExecute=true});
    install.Text="Installed";launch.Enabled=false;
   }catch(Exception ex){state.Text=ex.Message;MessageBox.Show(this,ex.Message,"Installation could not finish",MessageBoxButtons.OK,MessageBoxIcon.Warning);install.Enabled=true;}
   finally{Package.CleanTemp(stage);busy=false;}
  }
 }
 static class Program {
  [STAThread]static int Main(string[] args){
   Application.EnableVisualStyles();Application.SetCompatibleTextRenderingDefault(false);
   try{
    if(args.Length==2&&args[0]=="--extract"){Package.Extract(args[1]);return 0;}
    if(args.Length==1&&args[0]=="--uninstall"){Package.Uninstall();return 0;}
    Application.Run(new SetupForm());return 0;
   }catch(Exception ex){MessageBox.Show(ex.Message,"APC40 Bridge setup");return 1;}
  }
 }
}
