using System;
using System.IO;
using System.Drawing;
using System.Diagnostics;
using System.Collections.Generic;
using System.Threading.Tasks;
using System.Windows.Forms;
using Microsoft.Web.WebView2.Core;
using Microsoft.Web.WebView2.WinForms;
namespace ApcBridge {
 sealed class VisualizerPage : Form {
  readonly string home;
  readonly Panel surface=new Panel{Dock=DockStyle.Fill};
  readonly Label status=Theme.Label("Starting the local visualizer…",10,Theme.Muted);
  readonly Button retry=Theme.Button("Retry",false),runtime=Theme.Button("WebView2 setup help",true);
  WebView2 web; Uri local; bool loading,initialized;
  Task<bool> preparing; TaskCompletionSource<bool> prepared; string requestId;
  public bool ReadyToClose {get;private set;}
  public VisualizerPage(string path){
   home=path;Theme.Form(this,"APC40 Visualizer",new Size(1100,780));
   var footer=new TableLayoutPanel{Dock=DockStyle.Bottom,Height=44,ColumnCount=3,Padding=new Padding(12,5,5,5)};
   footer.ColumnStyles.Add(new ColumnStyle(SizeType.Percent,100));footer.ColumnStyles.Add(new ColumnStyle(SizeType.Absolute,90));footer.ColumnStyles.Add(new ColumnStyle(SizeType.Absolute,220));
   footer.Controls.Add(status,0,0);footer.Controls.Add(retry,1,0);footer.Controls.Add(runtime,2,0);runtime.Visible=false;
   Controls.Add(surface);Controls.Add(footer);
   retry.Click+=async(s,e)=>{if(!initialized||await PrepareCloseAsync())await LoadAsync();};runtime.Click+=async(s,e)=>await InstallRuntimeAsync();Shown+=async(s,e)=>await LoadAsync();
   Disposed+=(s,e)=>{if(web!=null)web.Dispose();if(prepared!=null)prepared.TrySetResult(false);};
  }
  bool Trusted(string address){
   Uri uri;return local!=null&&Uri.TryCreate(address,UriKind.Absolute,out uri)&&uri.Scheme=="http"&&uri.Host=="127.0.0.1"&&uri.Port==local.Port&&uri.AbsolutePath.StartsWith(local.AbsolutePath,StringComparison.Ordinal);
  }
  static string ViewerUrl(string home){
   string python=Path.Combine(home,"runtime","python.exe"),script=Path.Combine(home,"visualizer","launcher.py");
   if(!File.Exists(python)||!File.Exists(script))throw new IOException("The visualizer or bundled Python is missing. Run Install / repair.");
   var info=new ProcessStartInfo(python,"\""+script+"\" --url"){WorkingDirectory=home,UseShellExecute=false,CreateNoWindow=true,RedirectStandardOutput=true,RedirectStandardError=true};
   using(var process=Process.Start(info)){
    var output=process.StandardOutput.ReadToEndAsync();var error=process.StandardError.ReadToEndAsync();
    if(!process.WaitForExit(30000)){try{process.Kill();process.WaitForExit();}catch{}throw new IOException("The local visualizer did not start in time. Retry or check its logs.");}
    if(process.ExitCode!=0)throw new IOException(Backend.Tail(error.Result,1200));
    return Convert.ToString(Backend.Json.Deserialize<Dictionary<string,object>>(output.Result.Trim())["url"]);
   }
  }
  async Task LoadAsync(){
   if(loading||IsDisposed)return;loading=true;retry.Enabled=false;runtime.Visible=false;status.Text="Starting the local visualizer…";
   try{
    try{CoreWebView2Environment.GetAvailableBrowserVersionString();}catch(WebView2RuntimeNotFoundException){runtime.Visible=true;throw new IOException("WebView2 Runtime is required. Install it here, or use the offline Microsoft installer supplied with the package.");}
    string address=await Task.Run(()=>ViewerUrl(home));if(IsDisposed)return;
    Uri parsed;if(!Uri.TryCreate(address,UriKind.Absolute,out parsed)||parsed.Scheme!="http"||parsed.Host!="127.0.0.1"||parsed.IsDefaultPort||parsed.AbsolutePath=="/"||!parsed.AbsolutePath.EndsWith("/"))throw new IOException("Invalid local visualizer address.");local=parsed;
    if(web!=null){surface.Controls.Remove(web);web.Dispose();}
    initialized=false;ReadyToClose=false;preparing=null;web=new WebView2{Dock=DockStyle.Fill,DefaultBackgroundColor=Theme.Bg};surface.Controls.Add(web);
    string profile=Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),"APC40 Bridge","WebView2");
    var environment=await CoreWebView2Environment.CreateAsync(null,profile);if(IsDisposed)return;
    await web.EnsureCoreWebView2Async(environment);if(IsDisposed)return;
    var core=web.CoreWebView2;core.Settings.IsStatusBarEnabled=false;core.Settings.AreDefaultContextMenusEnabled=false;
    core.NavigationStarting+=(s,e)=>{if(!Trusted(e.Uri)){e.Cancel=true;status.Text="Only local visualizer pages can open inside Bridge.";}};
    core.FrameNavigationStarting+=(s,e)=>{if(!Trusted(e.Uri)&&e.Uri!="about:blank")e.Cancel=true;};
    core.NewWindowRequested+=(s,e)=>{e.Handled=true;Uri uri;if(e.IsUserInitiated&&Uri.TryCreate(e.Uri,UriKind.Absolute,out uri)&&(uri.Scheme=="https"||uri.Scheme=="http"))Process.Start(new ProcessStartInfo(e.Uri){UseShellExecute=true});};
    core.PermissionRequested+=(s,e)=>{
     if(!Trusted(core.Source)){e.State=CoreWebView2PermissionState.Deny;return;}
     if(e.PermissionKind==CoreWebView2PermissionKind.Camera){e.State=MessageBox.Show(this,"Allow this local visualizer to use cameras, including SpoutCam? Images stay on this computer.","Visualizer camera",MessageBoxButtons.YesNo,MessageBoxIcon.Question)==DialogResult.Yes?CoreWebView2PermissionState.Allow:CoreWebView2PermissionState.Deny;e.SavesInProfile=true;}
     else if(e.PermissionKind==CoreWebView2PermissionKind.Microphone)e.State=CoreWebView2PermissionState.Deny;
    };
    core.DownloadStarting+=(s,e)=>{
     e.Handled=true;
     using(var dialog=new SaveFileDialog{FileName=Path.GetFileName(e.ResultFilePath),Title="Save visualizer file",InitialDirectory=Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.UserProfile),"Downloads")}){
      if(dialog.ShowDialog(this)!=DialogResult.OK){e.Cancel=true;return;}e.ResultFilePath=dialog.FileName;
     }
    };
    core.WebMessageReceived+=(s,e)=>{
     if(!Trusted(e.Source))return;
     try{var data=Backend.Json.Deserialize<Dictionary<string,object>>(e.WebMessageAsJson);if(Convert.ToString(data["type"])=="prepared"&&Convert.ToString(data["id"])==requestId&&prepared!=null){bool ok=Backend.Flag(data,"ok");if(!ok)status.Text=Convert.ToString(data["error"]);prepared.TrySetResult(ok);}}catch{}
    };
    core.NavigationCompleted+=(s,e)=>{initialized=e.IsSuccess;status.Text=e.IsSuccess?"Local workspace · Visualizer / Output mapping / 3D Editor":"Could not load the visualizer: "+e.WebErrorStatus;};
    core.ProcessFailed+=(s,e)=>{initialized=false;status.Text="The renderer stopped. Saved projects remain available. Use Retry to reopen it.";};
    core.Navigate(new Uri(local,"preview.html").AbsoluteUri);
   }catch(Exception ex){if(!IsDisposed)status.Text=ex.Message;}
   finally{loading=false;if(!IsDisposed)retry.Enabled=true;}
  }
  Task InstallRuntimeAsync(){
   MessageBox.Show(this,"Install Microsoft WebView2 Runtime using the offline installer in the package's dependencies folder, then choose Retry. The official download is at developer.microsoft.com/microsoft-edge/webview2.","WebView2 setup",MessageBoxButtons.OK,MessageBoxIcon.Information);
   return Task.FromResult(0);
  }
  public async Task<bool> PrepareCloseAsync(){
   if(ReadyToClose)return true;if(preparing!=null)return await preparing;
   var pending=new TaskCompletionSource<bool>();preparing=pending.Task;
   try{bool ok=await FlushAsync();pending.TrySetResult(ok);return ok;}finally{preparing=null;}
  }
  async Task<bool> FlushAsync(){
   if(!initialized||web==null||web.CoreWebView2==null){ReadyToClose=true;return true;}
   try{
    status.Text="Saving the local workspace before leaving…";prepared=new TaskCompletionSource<bool>();requestId=Guid.NewGuid().ToString("N");
    web.CoreWebView2.PostWebMessageAsJson(Backend.Json.Serialize(new{type="prepare-close",id=requestId}));
    var completed=await Task.WhenAny(prepared.Task,Task.Delay(30000));
    if(completed!=prepared.Task||!await prepared.Task)throw new IOException("The editor could not confirm that your work is saved. Save a GLB project, then try again.");
    ReadyToClose=true;return true;
   }catch(Exception ex){if(!IsDisposed){status.Text=ex.Message;var leave=MessageBox.Show(this,ex.Message+"\n\nLeave without saving local recovery? Any unsaved edits may be lost. Choose No to stay in the editor.","Workspace not saved",MessageBoxButtons.YesNo,MessageBoxIcon.Warning,MessageBoxDefaultButton.Button2);if(leave==DialogResult.Yes){ReadyToClose=true;return true;}}return false;}
   finally{prepared=null;}
  }
 }
}
