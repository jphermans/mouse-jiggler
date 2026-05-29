import AppKit
import CoreGraphics

// ═══════════════════════════════════════════════════════════════════════════
//  Mouse Jiggler — macOS menu bar app
//  Compile: swiftc -framework AppKit -framework CoreGraphics -o MouseJiggler mouse_jiggler_macos.swift
// ═══════════════════════════════════════════════════════════════════════════

let APP_NAME = "Mouse Jiggler"
let CONFIG_DIR = FileManager.default.homeDirectoryForCurrentUser
    .appendingPathComponent("Library/Application Support/\(APP_NAME)")
let CONFIG_FILE = CONFIG_DIR.appendingPathComponent("config.json")

struct Config: Codable {
    var interval: Double = 60
    var pixels: Int = 3
    var enabled: Bool = true
}

func loadConfig() -> Config {
    guard let data = try? Data(contentsOf: CONFIG_FILE),
          let config = try? JSONDecoder().decode(Config.self, from: data)
    else { return Config() }
    return config
}

func saveConfig(_ config: Config) {
    try? FileManager.default.createDirectory(at: CONFIG_DIR, withIntermediateDirectories: true)
    if let data = try? JSONEncoder().encode(config) {
        try? data.write(to: CONFIG_FILE)
    }
}

// ── Mouse Movement ───────────────────────────────────────────────────────
func jiggleMouse(pixels: Int) {
    let dx = Int.random(in: 1...max(1, pixels)) * (Bool.random() ? 1 : -1)
    let dy = Int.random(in: 1...max(1, pixels)) * (Bool.random() ? 1 : -1)

    guard let event = CGEvent(source: nil) else { return }
    let loc = event.location
    let newPoint = CGPoint(x: loc.x + CGFloat(dx), y: loc.y + CGFloat(dy))

    guard let moveEvent = CGEvent(
        mouseEventSource: nil,
        mouseType: .mouseMoved,
        mouseCursorPosition: newPoint,
        mouseButton: .left
    ) else { return }

    moveEvent.post(tap: .cghidEventTap)
}

// ── Menu Bar Icon ────────────────────────────────────────────────────────
func makeIconImage() -> NSImage {
    let size = NSSize(width: 18, height: 18)
    let image = NSImage(size: size)
    image.isTemplate = true

    image.lockFocus()
    NSColor.controlTextColor.setFill()
    let path = NSBezierPath()
    path.move(to: NSPoint(x: 3, y: 2))
    path.line(to: NSPoint(x: 3, y: 13))
    path.line(to: NSPoint(x: 7, y: 10))
    path.line(to: NSPoint(x: 10, y: 15))
    path.line(to: NSPoint(x: 13, y: 13))
    path.line(to: NSPoint(x: 8, y: 8))
    path.line(to: NSPoint(x: 12, y: 5))
    path.close()
    path.fill()
    image.unlockFocus()
    return image
}

// ═══════════════════════════════════════════════════════════════════════════
//  App Delegate
// ═══════════════════════════════════════════════════════════════════════════
@main
class AppDelegate: NSObject, NSApplicationDelegate {
    var statusItem: NSStatusItem!
    var config = loadConfig()
    var running = false
    var paused = false
    var jiggleThread: Thread?

    func applicationDidFinishLaunching(_ notification: Notification) {
        NSApp.setActivationPolicy(.accessory)

        statusItem = NSStatusBar.system.statusItem(withLength: NSStatusItem.variableLength)
        statusItem.button?.image = makeIconImage()
        rebuildMenu()

        if config.enabled {
            startJiggling()
        }
    }

    func rebuildMenu() {
        let menu = NSMenu()
        menu.autoenablesItems = false

        // Pause / Resume
        let pauseItem = NSMenuItem(
            title: paused ? "▶ Resume" : "⏸ Pause",
            action: #selector(togglePause),
            keyEquivalent: ""
        )
        pauseItem.target = self
        menu.addItem(pauseItem)

        menu.addItem(NSMenuItem.separator())

        // Interval
        let intervalItem = NSMenuItem(title: "Interval", action: nil, keyEquivalent: "")
        let intervalMenu = NSMenu()
        for secs in [30, 60, 120, 300, 600] {
            let label = secs < 120 ? "\(secs)s" : "\(secs / 60)min"
            let item = NSMenuItem(title: label, action: #selector(setInterval(_:)), keyEquivalent: "")
            item.target = self; item.state = Int(config.interval) == secs ? .on : .off; item.tag = secs
            intervalMenu.addItem(item)
        }
        intervalItem.submenu = intervalMenu
        menu.addItem(intervalItem)

        // Pixels
        let pixelsItem = NSMenuItem(title: "Pixels", action: nil, keyEquivalent: "")
        let pixelsMenu = NSMenu()
        for px in [1, 2, 3, 5, 10] {
            let item = NSMenuItem(title: "\(px)px", action: #selector(setPixels(_:)), keyEquivalent: "")
            item.target = self; item.state = config.pixels == px ? .on : .off; item.tag = px
            pixelsMenu.addItem(item)
        }
        pixelsItem.submenu = pixelsMenu
        menu.addItem(pixelsItem)

        menu.addItem(NSMenuItem.separator())

        // Config
        let configItem = NSMenuItem(title: "Open Config File", action: #selector(openConfig), keyEquivalent: "")
        configItem.target = self
        menu.addItem(configItem)

        menu.addItem(NSMenuItem.separator())

        // Quit
        let quitItem = NSMenuItem(title: "Quit", action: #selector(quitApp), keyEquivalent: "q")
        quitItem.target = self
        menu.addItem(quitItem)

        statusItem.menu = menu
    }

    // ── Jiggle Thread ──────────────────────────────────────────────────
    func startJiggling() {
        guard !running else { return }
        running = true; paused = false
        jiggleThread = Thread { [weak self] in
            while self?.running == true {
                if self?.paused == false {
                    jiggleMouse(pixels: self?.config.pixels ?? 3)
                }
                Thread.sleep(forTimeInterval: self?.config.interval ?? 60)
            }
        }
        jiggleThread?.start()
    }

    // ── Menu Actions ───────────────────────────────────────────────────
    @objc func togglePause() { paused.toggle(); rebuildMenu() }
    @objc func setInterval(_ sender: NSMenuItem) { config.interval = Double(sender.tag); saveConfig(config); rebuildMenu() }
    @objc func setPixels(_ sender: NSMenuItem) { config.pixels = sender.tag; saveConfig(config); rebuildMenu() }

    @objc func openConfig() {
        try? FileManager.default.createDirectory(at: CONFIG_DIR, withIntermediateDirectories: true)
        if !FileManager.default.fileExists(atPath: CONFIG_FILE.path) { saveConfig(config) }
        NSWorkspace.shared.open(CONFIG_FILE)
    }

    @objc func quitApp() { running = false; NSApp.terminate(nil) }
}
