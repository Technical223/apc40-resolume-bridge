import Cocoa
import WebKit

final class AppDelegate: NSObject, NSApplicationDelegate, NSWindowDelegate, WKUIDelegate {
    var window: NSWindow!
    func applicationDidFinishLaunching(_ notification: Notification) {
        guard CommandLine.arguments.count == 2,
              let url = URL(string: CommandLine.arguments[1]), url.host == "127.0.0.1" else {
            NSApp.terminate(nil); return
        }
        let menu = NSMenu(), applicationMenu = NSMenu()
        let root = NSMenuItem(); root.submenu = applicationMenu; menu.addItem(root)
        applicationMenu.addItem(withTitle: "About APC40 Bridge", action: #selector(about), keyEquivalent: "")
        applicationMenu.addItem(NSMenuItem.separator())
        applicationMenu.addItem(withTitle: "Quit APC40 Bridge", action: #selector(NSApplication.terminate(_:)), keyEquivalent: "q")
        NSApp.mainMenu = menu
        window = NSWindow(contentRect: NSRect(x: 0,y: 0,width: 1160,height: 780),
            styleMask: [.titled,.closable,.miniaturizable,.resizable], backing: .buffered, defer: false)
        window.title = "APC40 Bridge — macOS Test Build"
        window.minSize = NSSize(width: 960,height: 680);window.delegate = self
        window.appearance = NSAppearance(named: .darkAqua)
        let view = WKWebView(frame: window.contentView!.bounds)
        view.uiDelegate = self
        view.autoresizingMask = [.width,.height]
        window.contentView = view; view.load(URLRequest(url: url))
        window.center();window.makeKeyAndOrderFront(nil);NSApp.activate(ignoringOtherApps: true)
    }
    func windowShouldClose(_ sender: NSWindow) -> Bool {
        sender.orderOut(nil);return false
    }
    func applicationShouldHandleReopen(_ sender: NSApplication, hasVisibleWindows flag: Bool) -> Bool {
        window.makeKeyAndOrderFront(nil);return true
    }
    func webView(_ webView: WKWebView, runJavaScriptConfirmPanelWithMessage message: String, initiatedByFrame frame: WKFrameInfo, completionHandler: @escaping (Bool) -> Void) {
        let alert = NSAlert();alert.messageText = "APC40 Bridge";alert.informativeText = message
        alert.addButton(withTitle: "Continue");alert.addButton(withTitle: "Cancel")
        completionHandler(alert.runModal() == .alertFirstButtonReturn)
    }
    func webView(_ webView: WKWebView, runOpenPanelWith parameters: WKOpenPanelParameters, initiatedByFrame frame: WKFrameInfo, completionHandler: @escaping ([URL]?) -> Void) {
        let panel = NSOpenPanel();panel.allowsMultipleSelection = false;panel.canChooseDirectories = false;panel.allowedFileTypes = ["json"]
        panel.beginSheetModal(for: window) { response in completionHandler(response == .OK ? panel.urls : nil) }
    }
    @objc func about() {
        let alert = NSAlert();alert.messageText = "APC40 Bridge — macOS test build"
        alert.informativeText = "Diagnostics stay on this Mac. Nothing is uploaded automatically. Use Export diagnostics and share the ZIP manually if you choose. Closing the window keeps the app running; Quit stops the bridge."
        alert.runModal()
    }
}
let app = NSApplication.shared
let delegate = AppDelegate();app.delegate = delegate
app.setActivationPolicy(.regular);app.run()
