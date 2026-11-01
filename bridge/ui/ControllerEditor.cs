using System;
using System.IO;
using System.Linq;
using System.Text;
using System.Drawing;
using System.Drawing.Drawing2D;
using System.Collections;
using System.Collections.Generic;
using System.Windows.Forms;

namespace ApcBridge {
    sealed class SurfaceControl {
        public string Id, Name, Kind;
        public int Channel, Number;
        public RectangleF Bounds;
        public bool Rgb;
        public bool Source { get { return Kind!="button"; } }
        public override string ToString() { return Name; }
    }
    static class SurfaceMap {
        public static List<SurfaceControl> Build() {
            // Hotspots use the supplied top-view image's native 1600 x 992 coordinates.
            var c=new List<SurfaceControl>();
            for(int col=0;col<8;col++) {
                float x=33+120.3f*col;
                c.Add(Source("Hue knob "+(col+1),"knob",0,48+col,38+121*col,44,87,94));
                for(int row=0;row<5;row++)c.Add(Button("Grid "+(row+1)+" / "+(col+1),0,(4-row)*8+col,x,164+58.3f*row,108,41,true));
                c.Add(Button("Clip stop "+(col+1),col,52,57+120*col,461,65,37,false));
                c.Add(Button("Track select "+(col+1),col,51,x,526,108,34,false));
                c.Add(Button("Activator "+(col+1),col,50,37+120*col,585,43,34,false));
                c.Add(Button("Crossfader assign "+(col+1),col,66,98+120*col,585,43,34,false));
                c.Add(Button("Solo "+(col+1),col,49,37+120*col,637,43,34,false));
                c.Add(Button("Record arm "+(col+1),col,48,98+120*col,637,43,34,false));
                c.Add(Source("Track fader "+(col+1),"fader",col,7,47+120*col,700,80,218));
            }
            for(int row=0;row<5;row++)c.Add(Button("Scene launch "+(row+1),0,82+row,995,175+57*row,61,37,true));
            string[] upper={"Device left","Device right","Bank left","Bank right"};
            string[] lower={"Device on/off","Device lock","Clip / device view","Detail view"};
            for(int i=0;i<8;i++){
                int col=i%4,row=i/4;
                c.Add(Source("Device knob "+(i+1),"knob",0,16+i,1103+121*col,351+121*row,87,87));
                c.Add(Button(row==0?upper[col]:lower[col],0,58+i,1116+121*col,596+66*row,46,23,false));
            }
            c.Add(Source("Master fader","fader",0,14,991,701,74,218));
            c.Add(Source("Crossfader","crossfader",0,15,1265,852,248,85));
            c.Add(Source("Cue level","knob",0,47,988,587,79,81));
            c.Add(Button("Master",0,80,995,532,61,30,false));
            c.Add(Button("Pan",0,87,1119,152,47,24,false));
            c.Add(Button("Sends",0,88,1119,222,47,23,false));
            c.Add(Button("User",0,89,1119,286,47,23,false));
            c.Add(Button("Metronome",0,90,1237,222,49,23,false));
            c.Add(Button("Play",0,91,1238,130,49,40,false));
            c.Add(Button("Record",0,93,1359,130,49,40,false));
            c.Add(Button("Up",0,94,1150,736,50,33,false));
            c.Add(Button("Down",0,95,1150,790,50,29,false));
            c.Add(Button("Right",0,96,1204,736,29,82,false));
            c.Add(Button("Left",0,97,1116,736,29,82,false));
            c.Add(Button("Shift",0,98,1354,730,48,24,false));
            c.Add(Button("Tap tempo",0,99,1359,221,49,24,false));
            c.Add(Button("Nudge down",0,100,1237,286,49,23,false));
            c.Add(Button("Nudge up",0,101,1359,286,49,23,false));
            c.Add(Button("Session record",0,102,1481,129,49,41,false));
            c.Add(Button("Bank lock",0,103,1474,731,49,24,false));
            return c;
        }
        static SurfaceControl Button(string n,int ch,int note,float x,float y,float w,float h,bool rgb) {
            return new SurfaceControl{Id="n:"+ch+":"+note,Name=n,Kind="button",Channel=ch,Number=note,Bounds=new RectangleF(x,y,w,h),Rgb=rgb};
        }
        static SurfaceControl Source(string n,string kind,int ch,int cc,float x,float y,float w,float h) {
            return new SurfaceControl{Id="c:"+ch+":"+cc,Name=n,Kind=kind,Channel=ch,Number=cc,Bounds=new RectangleF(x,y,w,h)};
        }
    }
    sealed class LightingRule {
        public int Channel,Note,SourceChannel,SourceCc,Color=5,Reset;
        public string Mode="solid",Press="passthrough";
        public decimal Slow=1,Fast=3;
        public Dictionary<string,object> Json() {
            return new Dictionary<string,object>{{"channel",Channel},{"note",Note},{"mode",Mode},{"color",Color},
                {"source_channel",SourceChannel},{"source_cc",SourceCc},{"press",Press},{"reset_value",Reset},{"rate_min",Slow},{"rate_max",Fast}};
        }
        public static LightingRule Read(Dictionary<string,object> d) {
            return new LightingRule{Channel=Int(d,"channel",0),Note=Int(d,"note",0),Mode=Str(d,"mode","solid"),Color=Int(d,"color",5),
                SourceChannel=Int(d,"source_channel",0),SourceCc=Int(d,"source_cc",48),Press=Str(d,"press","passthrough"),
                Reset=Int(d,"reset_value",0),Slow=Dec(d,"rate_min",1),Fast=Dec(d,"rate_max",3)};
        }
        static int Int(Dictionary<string,object>d,string k,int def){return d.ContainsKey(k)?Convert.ToInt32(d[k]):def;}
        static decimal Dec(Dictionary<string,object>d,string k,decimal def){return d.ContainsKey(k)?Convert.ToDecimal(d[k]):def;}
        static string Str(Dictionary<string,object>d,string k,string def){return d.ContainsKey(k)?Convert.ToString(d[k]):def;}
    }
    sealed class PaletteChoice {
        public string Name;public int Value;public Color Color;
        public PaletteChoice(string n,int v,Color c){Name=n;Value=v;Color=c;}
        public override string ToString(){return Name;}
    }
    sealed class ControllerCanvas : Control {
        public readonly List<SurfaceControl> Items=SurfaceMap.Build();
        public Dictionary<string,LightingRule> Rules=new Dictionary<string,LightingRule>();
        public SurfaceControl Selected,Hover;
        public int PreviewValue=64;
        public bool DefaultLit=true,DefaultSpeed;
        public double HueLimit=.63871;
        public double Phase;
        public bool LiveMode,LiveRequested;
        public Dictionary<string,int> LiveLeds=new Dictionary<string,int>(),LiveValues=new Dictionary<string,int>();
        readonly Image photo;
        Bitmap photoCache;

        public event Action<SurfaceControl> Picked;
        readonly ToolTip tip=new ToolTip();
        float scale=1,ox,oy;
        static readonly Color[] hueColors={Color.FromArgb(239,86,104),Color.FromArgb(243,155,83),Color.FromArgb(239,218,102),Color.FromArgb(125,224,145),Color.FromArgb(73,202,183),Color.FromArgb(82,182,237),Color.FromArgb(111,132,242),Color.FromArgb(175,116,232)};
        public ControllerCanvas(){
            DoubleBuffered=true;ResizeRedraw=true;BackColor=Theme.Bg;Cursor=Cursors.Hand;AccessibleName="APC40 mkII controller layout";
            using(var stream=typeof(ControllerCanvas).Assembly.GetManifestResourceStream("ApcBridge.ControllerTop.jpg")){
                if(stream==null)throw new Exception("Controller image is missing from the app build.");
                using(var image=Image.FromStream(stream))photo=new Bitmap(image);
            }
        }
        public Color Led(SurfaceControl c) {
            int liveValue;
            if(LiveRequested&&!LiveMode)return Color.FromArgb(27,33,42);
            if(LiveMode){
                if(!LiveLeds.TryGetValue(c.Channel+":"+c.Number,out liveValue)||liveValue==0)return Color.FromArgb(27,33,42);
                if(!c.Rgb)return Color.FromArgb(211,224,231);
                return PaletteColor(liveValue);
            }
            LightingRule rule;
            if(Rules.TryGetValue(c.Id,out rule)) {
                if(rule.Mode=="off" || (rule.Mode=="level"&&PreviewValue==0))return Color.FromArgb(39,47,59);
                double hz=(double)rule.Slow+(rule.Mode=="speed"?((double)(rule.Fast-rule.Slow)*PreviewValue/127):0);
                if((rule.Mode=="speed"||rule.Mode=="blink")&&(Phase*hz)%1>=.5)return Color.FromArgb(39,47,59);
                if(rule.Mode=="hue")return Hue(PreviewValue/127.0*HueLimit);
                var pc=ControllerEditor.Palette.FirstOrDefault(p=>p.Value==rule.Color);
                return c.Rgb?(pc==null?Theme.Accent:pc.Color):Color.FromArgb(208,221,231);
            }
            if(c.Rgb && c.Number>=32&&c.Number<40)return hueColors[c.Number-32];
            if(c.Number>=58&&c.Number<=61&&DefaultSpeed)return (Phase*(1+2*PreviewValue/127.0))%1<.5?Theme.Accent:Color.FromArgb(39,47,59);
            return DefaultLit&&!c.Rgb?Color.FromArgb(130,152,164):Color.FromArgb(39,47,59);
        }
        static Color PaletteColor(int value){
            var exact=ControllerEditor.Palette.FirstOrDefault(p=>p.Value==value);
            if(exact!=null)return exact.Color;
            if(value<=3)return Color.FromArgb(170+value*20,170+value*20,170+value*20);
            if(value<=59)return Hue(Math.Max(0,(value-5)/56.0));
            return Color.FromArgb(142,170,188); // Other APC palette entries are approximate in the visual monitor.
        }
        static Color Hue(double h) {
            h=(h%1+1)%1;double t=h*6;int i=(int)t;double f=t-i;
            double r=0,g=0,b=0;
            switch(i){case 0:r=1;g=f;break;case 1:r=1-f;g=1;break;case 2:g=1;b=f;break;case 3:g=1-f;b=1;break;case 4:r=f;b=1;break;default:r=1;b=1-f;break;}
            return Color.FromArgb((int)(r*235),(int)(g*235),(int)(b*235));
        }
        protected override void OnPaint(PaintEventArgs e) {
            var g=e.Graphics;g.SmoothingMode=SmoothingMode.AntiAlias;g.Clear(Theme.Bg);
            scale=Math.Min((Width-12)/1600f,(Height-12)/992f);if(scale<=0)return;
            ox=(Width-1600*scale)/2;oy=(Height-992*scale)/2;
            int cacheWidth=Math.Max(1,(int)Math.Ceiling(1600*scale)),cacheHeight=Math.Max(1,(int)Math.Ceiling(992*scale));
            if(photoCache==null||photoCache.Width!=cacheWidth||photoCache.Height!=cacheHeight){
                if(photoCache!=null)photoCache.Dispose();
                photoCache=new Bitmap(cacheWidth,cacheHeight);
                using(var cacheGraphics=Graphics.FromImage(photoCache)){cacheGraphics.InterpolationMode=InterpolationMode.HighQualityBicubic;cacheGraphics.DrawImage(photo,new Rectangle(0,0,cacheWidth,cacheHeight));}
            }
            g.DrawImageUnscaled(photoCache,(int)ox,(int)oy);
            g.TranslateTransform(ox,oy);g.ScaleTransform(scale,scale);
            foreach(var c in Items){
                RectangleF b=c.Bounds;
                if(c.Source){
                    int value=LiveRequested&&!LiveMode?0:PreviewValue;
                    if(LiveMode&&!LiveValues.TryGetValue(c.Channel+":"+c.Number,out value))value=0;
                    if(c.Kind=="knob"){
                        using(var p=new Pen(Color.FromArgb(125,Theme.Accent),6))g.DrawArc(p,b,135,Math.Max(2,270*value/127));
                    }else if(c.Kind=="crossfader"){
                        float x=b.X+b.Width*value/127;
                        using(var p=new Pen(Color.FromArgb(170,Theme.Accent),5))g.DrawLine(p,x,b.Y+8,x,b.Bottom-8);
                    }else{
                        float y=b.Bottom-b.Height*value/127;
                        using(var p=new Pen(Color.FromArgb(170,Theme.Accent),5))g.DrawLine(p,b.X+6,y,b.Right-6,y);
                    }
                }else{
                    Color led=Led(c);Fill(g,b,Color.FromArgb(led.R<50&&led.G<50&&led.B<65?225:210,led),4);
                    if(Rules.ContainsKey(c.Id))using(var br=new SolidBrush(Theme.Accent))g.FillEllipse(br,b.Right-9,b.Y-5,10,10);
                }
                if(c==Selected||c==Hover){RectangleF border=b;border.Inflate(5,5);using(var pen=new Pen(c==Selected?Theme.Accent:Theme.Muted,c==Selected?4:2))g.DrawRectangle(pen,border.X,border.Y,border.Width,border.Height);}
            }
        }
        internal static void Fill(Graphics g,RectangleF r,Color c,float radius){
            using(var b=new SolidBrush(c))using(var p=new GraphicsPath()){float d=radius*2;p.AddArc(r.X,r.Y,d,d,180,90);p.AddArc(r.Right-d,r.Y,d,d,270,90);p.AddArc(r.Right-d,r.Bottom-d,d,d,0,90);p.AddArc(r.X,r.Bottom-d,d,d,90,90);p.CloseFigure();g.FillPath(b,p);}
        }
        static void TextAt(Graphics g,string t,float x,float y,float sz,Color c,bool bold){using(var f=new Font("Segoe UI",sz,bold?FontStyle.Bold:FontStyle.Regular))using(var b=new SolidBrush(c))g.DrawString(t,f,b,x,y);}
        protected override void OnMouseMove(MouseEventArgs e){base.OnMouseMove(e);var hit=Hit(e.Location);if(hit!=Hover){Hover=hit;tip.SetToolTip(this,hit==null?"":hit.Name+(hit.Source?" • Input source":" • Click to edit"));Invalidate();}}
        SurfaceControl Hit(Point p){if(scale<=0)return null;var q=new PointF((p.X-ox)/scale,(p.Y-oy)/scale);return Items.LastOrDefault(c=>c.Bounds.Contains(q));}
        protected override void OnMouseDown(MouseEventArgs e){base.OnMouseDown(e);var c=Hit(e.Location);if(c!=null&&e.Button==MouseButtons.Left&&Picked!=null)Picked(c);}
        protected override void Dispose(bool disposing){if(disposing){tip.Dispose();photo.Dispose();if(photoCache!=null)photoCache.Dispose();}base.Dispose(disposing);}
    }

    sealed class ControllerEditor : Form {
        public static readonly PaletteChoice[] Palette={
            new PaletteChoice("White",3,Color.FromArgb(220,227,235)),new PaletteChoice("Red",5,Color.FromArgb(237,74,89)),
            new PaletteChoice("Amber",9,Color.FromArgb(240,153,70)),new PaletteChoice("Yellow",13,Color.FromArgb(239,218,86)),
            new PaletteChoice("Lime",17,Color.FromArgb(173,220,87)),new PaletteChoice("Green",21,Color.FromArgb(79,206,128)),
            new PaletteChoice("Mint",29,Color.FromArgb(69,209,177)),new PaletteChoice("Cyan",37,Color.FromArgb(68,190,219)),
            new PaletteChoice("Blue",45,Color.FromArgb(76,125,231)),new PaletteChoice("Violet",49,Color.FromArgb(149,111,229)),
            new PaletteChoice("Magenta",53,Color.FromArgb(214,99,220)),new PaletteChoice("Rose",57,Color.FromArgb(232,103,163))
        };
        readonly string home,file;
        string original;
        readonly Dictionary<string,LightingRule> rules=new Dictionary<string,LightingRule>();
        readonly ControllerCanvas canvas;
        readonly Label selectedName,detail,notice,previewCaption,summary;
        readonly ComboBox behavior,source,color,press;
        readonly NumericUpDown slow,fast,reset;
        readonly TextBox profileName;
        readonly TrackBar preview;
        readonly CheckBox live;
        DateTime lastLiveRead=DateTime.MinValue,lastLiveRequest=DateTime.MinValue;
        readonly Button pickSource,defaults,save;
        readonly System.Windows.Forms.Timer timer=new System.Windows.Forms.Timer();
        readonly TableLayoutPanel fields;
        readonly DateTime began=DateTime.UtcNow;
        SurfaceControl selected;
        bool loading,dirty,picking;
        static readonly string[] ModeNames={"Default bridge","LED off","Solid light","Follow Hue","Follow level (on / off)","Blink","Speed indicator"};
        static readonly string[] ModeKeys={"inherit","off","solid","hue","level","blink","speed"};
        public ControllerEditor(string path) {
            home=path;file=Path.Combine(home,"config.json");original=File.ReadAllText(file,Encoding.UTF8);
            var config=Backend.Json.Deserialize<Dictionary<string,object>>(original);
            Theme.Form(this,"Controller Studio • APC40 Bridge",new Size(1360,850));MinimumSize=new Size(1100,760);
            var root=new TableLayoutPanel{Dock=DockStyle.Fill,Padding=new Padding(24),ColumnCount=1,RowCount=3,Margin=Padding.Empty};
            root.RowStyles.Add(new RowStyle(SizeType.Absolute,76));root.RowStyles.Add(new RowStyle(SizeType.Percent,100));root.RowStyles.Add(new RowStyle(SizeType.Absolute,64));Controls.Add(root);
            var header=new TableLayoutPanel{Dock=DockStyle.Fill,ColumnCount=4,RowCount=2,Margin=Padding.Empty};
            header.ColumnStyles.Add(new ColumnStyle(SizeType.Percent,100));header.ColumnStyles.Add(new ColumnStyle(SizeType.Absolute,210));header.ColumnStyles.Add(new ColumnStyle(SizeType.Absolute,150));header.ColumnStyles.Add(new ColumnStyle(SizeType.Absolute,150));
            header.RowStyles.Add(new RowStyle(SizeType.Absolute,36));header.RowStyles.Add(new RowStyle(SizeType.Absolute,26));
            header.Controls.Add(Theme.Label("Controller Studio",24,Theme.Text),0,0);
            header.Controls.Add(Theme.Label("Your controller. Your lighting. No code required.",10,Theme.Muted),0,1);
            profileName=Theme.Input(config.ContainsKey("controller_profile_name")?Convert.ToString(config["controller_profile_name"]):"My APC40");profileName.MaxLength=60;profileName.AccessibleName="Profile name";profileName.Margin=new Padding(0,0,12,0);header.Controls.Add(profileName,1,0);
            var import=Theme.Button("Import profile",false);var export=Theme.Button("Export profile",false);import.Font=export.Font=new Font("Segoe UI",9);
            header.Controls.Add(import,2,0);header.Controls.Add(export,3,0);root.Controls.Add(header,0,0);
            var body=new TableLayoutPanel{Dock=DockStyle.Fill,ColumnCount=2,RowCount=1,Margin=Padding.Empty};
            body.ColumnStyles.Add(new ColumnStyle(SizeType.Percent,100));body.ColumnStyles.Add(new ColumnStyle(SizeType.Absolute,316));root.Controls.Add(body,0,1);
            canvas=new ControllerCanvas{Dock=DockStyle.Fill,Rules=rules,DefaultLit=!config.ContainsKey("always_lit")||Convert.ToBoolean(config["always_lit"]),DefaultSpeed=config.ContainsKey("speed_button_pulse")&&Convert.ToBoolean(config["speed_button_pulse"]),HueLimit=config.ContainsKey("hue_max")?Convert.ToDouble(config["hue_max"]):.63871};
            var left=new TableLayoutPanel{Dock=DockStyle.Fill,ColumnCount=1,RowCount=2,Margin=new Padding(0,0,20,0)};left.RowStyles.Add(new RowStyle(SizeType.Percent,100));left.RowStyles.Add(new RowStyle(SizeType.Absolute,70));left.Controls.Add(canvas,0,0);body.Controls.Add(left,0,0);
            var previewPanel=new TableLayoutPanel{Dock=DockStyle.Fill,ColumnCount=2,RowCount=2,Padding=new Padding(12,4,12,4),BackColor=Theme.Card};
            previewPanel.ColumnStyles.Add(new ColumnStyle(SizeType.Absolute,175));previewPanel.ColumnStyles.Add(new ColumnStyle(SizeType.Percent,100));previewPanel.RowStyles.Add(new RowStyle(SizeType.Absolute,24));previewPanel.RowStyles.Add(new RowStyle(SizeType.Absolute,32));
            previewCaption=Theme.Label("PREVIEW  ·  50%",9,Theme.Accent);previewPanel.Controls.Add(previewCaption,0,0);live=new CheckBox{Text="Live bridge feedback",ForeColor=Theme.Muted,Dock=DockStyle.Fill,AccessibleName="Live bridge feedback"};
            previewPanel.Controls.Add(live,1,0);
            preview=new TrackBar{Minimum=0,Maximum=127,Value=64,TickStyle=TickStyle.None,Dock=DockStyle.Fill,BackColor=Theme.Card,AccessibleName="Simulated input value"};previewPanel.Controls.Add(preview,0,1);previewPanel.SetColumnSpan(preview,2);left.Controls.Add(previewPanel,0,1);
            var inspector=new Panel{Dock=DockStyle.Fill,BackColor=Theme.Card,Padding=new Padding(18),AutoScroll=true};body.Controls.Add(inspector,1,0);
            fields=new TableLayoutPanel{Dock=DockStyle.Top,ColumnCount=1,RowCount=21,AutoSize=true,Margin=Padding.Empty};
            inspector.Controls.Add(fields);
            selectedName=Theme.Label("Select a control",17,Theme.Text);Add(selectedName,52);
            detail=Theme.Label("Click a pad, utility button, knob or fader on the controller.",9,Theme.Muted);Add(detail,58);
            Add(Theme.Label("LIGHTING",8,Theme.Accent),25);
            behavior=Combo(ModeNames.Cast<object>().ToArray());Add(behavior,36);
            Add(Theme.Label("Input source",9,Theme.Muted),25);
            source=Combo(canvas.Items.Where(c=>c.Source).Cast<object>().ToArray());Add(source,34);
            pickSource=Theme.Button("Pick source on controller",false);pickSource.Font=new Font("Segoe UI",9);Add(pickSource,35);
            Add(Theme.Label("LED color",9,Theme.Muted),25);color=Combo(Palette.Cast<object>().ToArray());Add(color,34);
            var rates=new TableLayoutPanel{Dock=DockStyle.Fill,ColumnCount=2,RowCount=2,Margin=Padding.Empty};rates.ColumnStyles.Add(new ColumnStyle(SizeType.Percent,50));rates.ColumnStyles.Add(new ColumnStyle(SizeType.Percent,50));
            rates.RowStyles.Add(new RowStyle(SizeType.Absolute,25));rates.RowStyles.Add(new RowStyle(SizeType.Absolute,32));
            rates.Controls.Add(Theme.Label("Slow / Hz",9,Theme.Muted),0,0);rates.Controls.Add(Theme.Label("Fast / Hz",9,Theme.Muted),1,0);
            slow=Number(.2m,5,1);fast=Number(.2m,5,3);rates.Controls.Add(slow,0,1);rates.Controls.Add(fast,1,1);Add(rates,62);
            Add(Theme.Label("BUTTON PRESS",8,Theme.Accent),30);
            press=Combo(new object[]{"Keep original Arena action","Reset source value"});Add(press,34);
            Add(Theme.Label("Reset position  ·  0 left / 127 right",9,Theme.Muted),28);reset=Number(0,127,0);reset.DecimalPlaces=0;Add(reset,32);
            summary=Theme.Label("",9,Theme.Muted);Add(summary,58);
            defaults=Theme.Button("Use default behavior",false);defaults.Font=new Font("Segoe UI",9);Add(defaults,36);
            var footer=new TableLayoutPanel{Dock=DockStyle.Fill,ColumnCount=2,RowCount=1,Padding=new Padding(0,14,0,0),Margin=Padding.Empty};footer.ColumnStyles.Add(new ColumnStyle(SizeType.Percent,100));footer.ColumnStyles.Add(new ColumnStyle(SizeType.Absolute,180));
            notice=Theme.Label("Preview safely. Save changes, then restart the bridge to apply.",9,Theme.Muted);footer.Controls.Add(notice,0,0);
            save=Theme.Button("Save changes",true);footer.Controls.Add(save,1,0);root.Controls.Add(footer,0,2);
            loading=true;ReadRules(config);profileName.TextChanged+=(s,e)=>Changed();loading=false;
            canvas.Picked+=SelectControl;
            live.CheckedChanged+=(s,e)=>{preview.Enabled=!live.Checked;lastLiveRead=DateTime.MinValue;UpdateLive();canvas.Invalidate();};
            preview.ValueChanged+=(s,e)=>{canvas.PreviewValue=preview.Value;if(!live.Checked)previewCaption.Text="PREVIEW  ·  "+Math.Round(preview.Value/127.0*100)+"%";canvas.Invalidate();};
            behavior.SelectedIndexChanged+=(s,e)=>Edit();source.SelectedIndexChanged+=(s,e)=>Edit();color.SelectedIndexChanged+=(s,e)=>Edit();press.SelectedIndexChanged+=(s,e)=>Edit();
            slow.ValueChanged+=(s,e)=>Edit();fast.ValueChanged+=(s,e)=>Edit();reset.ValueChanged+=(s,e)=>Edit();
            pickSource.Click+=(s,e)=>{picking=true;notice.Text="Click a knob or fader on the controller to link it.";};
            defaults.Click+=(s,e)=>{if(selected!=null&&!selected.Source){rules.Remove(selected.Id);Changed();LoadSelection();canvas.Invalidate();}};
            save.Click+=(s,e)=>Save();
            export.Click+=(s,e)=>Export();import.Click+=(s,e)=>Import();
            timer.Interval=100;timer.Tick+=(s,e)=>{if(WindowState==FormWindowState.Minimized)return;UpdateLive();canvas.Phase=(DateTime.UtcNow-began).TotalSeconds;if(canvas.LiveMode||canvas.DefaultSpeed||rules.Values.Any(x=>x.Mode=="blink"||x.Mode=="speed"))canvas.Invalidate();};timer.Start();
            FormClosing+=(s,e)=>{if(dirty&&MessageBox.Show(this,"Close without saving the controller changes?","Unsaved profile",MessageBoxButtons.YesNo,MessageBoxIcon.Question)!=DialogResult.Yes)e.Cancel=true;};
            FormClosed+=(s,e)=>timer.Dispose();
            SelectControl(canvas.Items.First(c=>c.Id=="n:0:32"));
        }
        void UpdateLive(){
            canvas.LiveRequested=live.Checked;
            if(live.Checked&&(DateTime.UtcNow-lastLiveRequest).TotalSeconds>=2){
                try{double expiry=(DateTime.UtcNow-new DateTime(1970,1,1)).TotalSeconds+5;File.WriteAllText(Path.Combine(home,"controller-live-request.json"),Backend.Json.Serialize(new Dictionary<string,object>{{"expires",expiry}}));lastLiveRequest=DateTime.UtcNow;}catch{}
            }
            if(!live.Checked){canvas.LiveMode=false;previewCaption.Text="PREVIEW  ·  "+Math.Round(preview.Value/127.0*100)+"%";return;}
            try {
                string path=Path.Combine(home,"controller-live.json");
                if(!File.Exists(path)){canvas.LiveMode=false;canvas.Invalidate();previewCaption.Text="LIVE  ·  Bridge offline";return;}
                DateTime modified=File.GetLastWriteTimeUtc(path);
                if((DateTime.UtcNow-modified).TotalSeconds>3){canvas.LiveMode=false;canvas.Invalidate();previewCaption.Text="LIVE  ·  Waiting for bridge";return;}
                if(modified==lastLiveRead)return;
                var data=Backend.Json.Deserialize<Dictionary<string,object>>(File.ReadAllText(path,Encoding.UTF8));
                canvas.LiveMode=data.ContainsKey("connected")&&Convert.ToBoolean(data["connected"]);
                if(canvas.LiveMode){
                    canvas.LiveLeds=LiveMap(data,"leds");canvas.LiveValues=LiveMap(data,"controls");previewCaption.Text="LIVE  ·  Bridge output";
                }else previewCaption.Text="LIVE  ·  Bridge offline";
                lastLiveRead=modified;
            }catch(IOException){previewCaption.Text="LIVE  ·  Updating…";}
            catch{canvas.LiveMode=false;previewCaption.Text="LIVE  ·  Unavailable";}
        }
        static Dictionary<string,int> LiveMap(Dictionary<string,object> data,string key){
            var result=new Dictionary<string,int>();object raw;
            if(data.TryGetValue(key,out raw)){
                var map=raw as Dictionary<string,object>;
                if(map!=null)foreach(var pair in map)result[pair.Key]=Math.Max(0,Math.Min(127,Convert.ToInt32(pair.Value)));
            }
            return result;
        }
        void Add(Control c,int height){int row=fields.Controls.Count;fields.RowStyles.Add(new RowStyle(SizeType.Absolute,height));c.Dock=DockStyle.Fill;c.Margin=new Padding(0,0,0,4);fields.Controls.Add(c,0,row);}
        static ComboBox Combo(object[] values){
            var c=new ComboBox{DropDownStyle=ComboBoxStyle.DropDownList,BackColor=Theme.Bg,ForeColor=Theme.Text,FlatStyle=FlatStyle.Flat,Dock=DockStyle.Fill,DrawMode=DrawMode.OwnerDrawFixed,ItemHeight=22};
            c.Items.AddRange(values);
            c.DrawItem+=(s,e)=>{
                if(e.Index<0)return;
                bool active=(e.State&DrawItemState.Selected)!=0;
                using(var bg=new SolidBrush(active?Color.FromArgb(43,69,68):Theme.Bg))e.Graphics.FillRectangle(bg,e.Bounds);
                Color ink=c.Enabled?Theme.Text:Theme.Muted;
                var pc=c.Items[e.Index] as PaletteChoice;int extra=0;
                if(pc!=null){using(var swatch=new SolidBrush(pc.Color))e.Graphics.FillRectangle(swatch,e.Bounds.X+7,e.Bounds.Y+6,12,12);extra=21;}
                using(var brush=new SolidBrush(ink))e.Graphics.DrawString(c.Items[e.Index].ToString(),c.Font,brush,e.Bounds.X+7+extra,e.Bounds.Y+4);
            };
            return c;
        }
        static NumericUpDown Number(decimal min,decimal max,decimal value){return new NumericUpDown{Minimum=min,Maximum=max,Value=value,DecimalPlaces=1,Increment=.1m,BackColor=Theme.Bg,ForeColor=Theme.Text,Dock=DockStyle.Fill,BorderStyle=BorderStyle.FixedSingle};}
        void Changed(){if(loading)return;dirty=true;notice.Text="Unsaved changes · preview only";save.Text="Save changes";canvas.Invalidate();}
        void SelectControl(SurfaceControl c){
            if(picking&&c.Source){picking=false;source.SelectedItem=c;notice.Text="Linked to "+c.Name+". Save and restart to apply.";return;}
            picking=false;selected=c;canvas.Selected=c;LoadSelection();canvas.Invalidate();
        }
        void LoadSelection(){
            loading=true;
            selectedName.Text=selected.Name;
            detail.Text=selected.Source?"Input source · use this control to drive a pad's color or blink rate. Ring feedback stays unchanged.":(selected.Rgb?"RGB pad · color and feedback":"Utility button · single-color LED");
            LightingRule rule;bool has=rules.TryGetValue(selected.Id,out rule);
            behavior.SelectedIndex=has?Array.IndexOf(ModeKeys,rule.Mode):0;
            if(rule==null)rule=new LightingRule{SourceCc=48+selected.Number%8};
            source.SelectedItem=canvas.Items.FirstOrDefault(c=>c.Source&&c.Channel==rule.SourceChannel&&c.Number==rule.SourceCc)??canvas.Items.First(c=>c.Source);
            color.SelectedItem=Palette.FirstOrDefault(c=>c.Value==rule.Color)??Palette[1];
            slow.Value=rule.Slow;fast.Value=rule.Fast;reset.Value=rule.Reset;press.SelectedIndex=rule.Press=="reset"?1:0;
            loading=false;Availability();
        }
        void Availability(){
            bool pad=selected!=null&&!selected.Source;string mode=behavior.SelectedIndex>=0?ModeKeys[behavior.SelectedIndex]:"inherit";
            behavior.Enabled=defaults.Enabled=pad;
            bool custom=pad&&mode!="inherit";bool needs=mode=="hue"||mode=="level"||mode=="speed"||press.SelectedIndex==1;
            source.Enabled=pickSource.Enabled=custom&&needs;color.Enabled=custom&&selected.Rgb&&mode!="off"&&mode!="hue";
            slow.Enabled=custom&&(mode=="blink"||mode=="speed");fast.Enabled=custom&&mode=="speed";
            press.Enabled=custom;reset.Enabled=custom&&press.SelectedIndex==1;
            summary.Text=!pad?"To create a link, select a target pad, choose a behavior, then use Pick source.":mode=="inherit"?"Uses the current bridge behavior, including existing Hue and speed settings.":press.SelectedIndex==1?"Reset replaces the original press and release. Position 0 is 1x for the supplied speed mapping.":"Lighting only. The original button action still reaches Arena.";
        }
        void Edit(){
            if(loading||selected==null||selected.Source)return;
            string mode=ModeKeys[Math.Max(0,behavior.SelectedIndex)];
            if(mode=="hue"&&!selected.Rgb){loading=true;behavior.SelectedIndex=2;loading=false;mode="solid";notice.Text="This button has a single-color LED. Choose an RGB grid pad for Hue.";}
            if(mode=="inherit")rules.Remove(selected.Id);
            else {
                var src=source.SelectedItem as SurfaceControl;var pc=color.SelectedItem as PaletteChoice;
                rules[selected.Id]=new LightingRule{Channel=selected.Channel,Note=selected.Number,Mode=mode,SourceChannel=src.Channel,SourceCc=src.Number,Color=pc.Value,Slow=slow.Value,Fast=fast.Value,Press=press.SelectedIndex==1?"reset":"passthrough",Reset=(int)reset.Value};
            }
            Changed();Availability();
        }
        void ValidateRules(){
            foreach(var rule in rules.Values)if(rule.Slow>rule.Fast)throw new Exception("Slow blink rate cannot exceed the fast rate.");
            if(string.IsNullOrWhiteSpace(profileName.Text))throw new Exception("Enter a profile name.");
        }
        object[] RuleArray(){return rules.Values.OrderBy(x=>x.Channel).ThenBy(x=>x.Note).Select(x=>(object)x.Json()).ToArray();}
        void Save(){
            try {
                ValidateRules();
                if(File.ReadAllText(file,Encoding.UTF8)!=original)throw new Exception("Bridge settings changed while this editor was open. Close and reopen Controller Studio before saving.");
                var cfg=Backend.Json.Deserialize<Dictionary<string,object>>(original);
                cfg["control_rules"]=RuleArray();cfg["controller_profile_name"]=profileName.Text.Trim();cfg["speed_ring_animation"]=false;
                string temp=file+".studio-"+Guid.NewGuid().ToString("N")+".tmp";
                try {File.WriteAllText(temp,Backend.Json.Serialize(cfg),new UTF8Encoding(false));File.Replace(temp,file,file+".before-studio-"+DateTime.Now.ToString("yyyyMMdd-HHmmss-fff")+".bak");}
                finally {if(File.Exists(temp))File.Delete(temp);}
                original=File.ReadAllText(file,Encoding.UTF8);dirty=false;notice.Text="Profile saved. Restart the bridge from the dashboard to apply.";save.Text="Saved";
            }catch(Exception ex){MessageBox.Show(this,ex.Message,"Could not save profile",MessageBoxButtons.OK,MessageBoxIcon.Warning);}
        }
        void ReadRules(Dictionary<string,object> document){
            var result=new Dictionary<string,LightingRule>();object raw;
            if(document.TryGetValue("control_rules",out raw)&&raw!=null){
                var array=raw as IEnumerable;if(array==null||raw is string)throw new Exception("Invalid profile rules.");
                foreach(object item in array){
                    var d=item as Dictionary<string,object>;if(d==null)throw new Exception("Invalid rule.");
                    var rule=LightingRule.Read(d);string id="n:"+rule.Channel+":"+rule.Note;
                    var target=canvas.Items.FirstOrDefault(c=>c.Id==id&&!c.Source);
                    if(target==null||result.ContainsKey(id)||!ModeKeys.Skip(1).Contains(rule.Mode)||(!target.Rgb&&rule.Mode=="hue")||rule.Slow<.2m||rule.Fast>5||rule.Slow>rule.Fast||rule.Reset<0||rule.Reset>127||rule.Color<1||rule.Color>127||!new[]{"passthrough","reset"}.Contains(rule.Press))throw new Exception("This profile contains an unsupported control or behavior.");
                    if(!Palette.Any(x=>x.Value==rule.Color))throw new Exception("This profile uses an unsupported editor palette color.");
                    if(!canvas.Items.Any(c=>c.Source&&c.Channel==rule.SourceChannel&&c.Number==rule.SourceCc))throw new Exception("This profile uses an unknown source.");
                    result.Add(id,rule);if(result.Count>160)throw new Exception("Too many profile rules.");
                }
            }
            rules.Clear();foreach(var pair in result)rules.Add(pair.Key,pair.Value);
        }
        void Export(){
            try {ValidateRules();using(var dialog=new SaveFileDialog{Title="Export controller profile",Filter="APC40 profile (*.json)|*.json",FileName="APC40-profile.json",OverwritePrompt=true}){
                if(dialog.ShowDialog(this)!=DialogResult.OK)return;
                var data=new Dictionary<string,object>{{"format","apc40-bridge-profile"},{"version",1},{"name",profileName.Text.Trim()},{"control_rules",RuleArray()}};
                File.WriteAllText(dialog.FileName,Backend.Json.Serialize(data),new UTF8Encoding(false));notice.Text="Profile exported. Your bridge settings were not changed.";
            }}catch(Exception ex){MessageBox.Show(this,ex.Message,"Could not export profile");}
        }
        void Import(){
            try {using(var dialog=new OpenFileDialog{Title="Import controller profile",Filter="APC40 profile (*.json)|*.json"}){
                if(dialog.ShowDialog(this)!=DialogResult.OK)return;
                if(new FileInfo(dialog.FileName).Length>262144)throw new Exception("Profile is too large.");
                var data=Backend.Json.Deserialize<Dictionary<string,object>>(File.ReadAllText(dialog.FileName,Encoding.UTF8));
                if(!data.ContainsKey("format")||Convert.ToString(data["format"])!="apc40-bridge-profile"||!data.ContainsKey("version")||Convert.ToInt32(data["version"])!=1||!data.ContainsKey("control_rules"))throw new Exception("Choose a supported APC40 Bridge profile.");
                ReadRules(data);loading=true;profileName.Text=data.ContainsKey("name")?Convert.ToString(data["name"]).Substring(0,Math.Min(60,Convert.ToString(data["name"]).Length)):"Imported profile";loading=false;
                Changed();LoadSelection();notice.Text="Profile imported into preview. Save changes to use it.";canvas.Invalidate();
            }}catch(Exception ex){MessageBox.Show(this,ex.Message,"Could not import profile");}
        }
    }
}
