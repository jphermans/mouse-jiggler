#import <Cocoa/Cocoa.h>
#import <CoreGraphics/CoreGraphics.h>
#import <ServiceManagement/ServiceManagement.h>

static NSString *APP_NAME = @"Mouse Jiggler";
static NSString *APP_VERSION = @"1.0.0";
static NSString *APP_CREATOR = @"Jean-Pierre Hermans";
static NSString *APP_WEBSITE = @"https://github.com/jphermans/mouse-jiggler";

// ── Config ───────────────────────────────────────────────────────────────
static NSString *configPath(void) {
    NSString *dir = [[NSSearchPathForDirectoriesInDomains(
        NSApplicationSupportDirectory, NSUserDomainMask, YES) firstObject]
        stringByAppendingPathComponent:APP_NAME];
    [[NSFileManager defaultManager] createDirectoryAtPath:dir
        withIntermediateDirectories:YES attributes:nil error:nil];
    return [dir stringByAppendingPathComponent:@"config.json"];
}

static NSDictionary *loadConfig(void) {
    NSData *data = [NSData dataWithContentsOfFile:configPath()];
    if (!data) return @{@"interval": @60, @"pixels": @3, @"enabled": @YES, @"launchAtLogin": @NO};
    NSDictionary *cfg = [NSJSONSerialization JSONObjectWithData:data options:0 error:nil];
    if (!cfg) return @{@"interval": @60, @"pixels": @3, @"enabled": @YES, @"launchAtLogin": @NO};
    // Ensure all keys exist with defaults
    NSMutableDictionary *m = [cfg mutableCopy];
    if (!m[@"interval"]) m[@"interval"] = @60;
    if (!m[@"pixels"]) m[@"pixels"] = @3;
    if (!m[@"enabled"]) m[@"enabled"] = @YES;
    if (!m[@"launchAtLogin"]) m[@"launchAtLogin"] = @NO;
    return m;
}

static void saveConfig(NSDictionary *config) {
    NSData *data = [NSJSONSerialization dataWithJSONObject:config options:NSJSONWritingPrettyPrinted error:nil];
    [data writeToFile:configPath() atomically:YES];
}

// ── Launch at Login ──────────────────────────────────────────────────────
static BOOL getLaunchAtLogin(void) {
    if (@available(macOS 13.0, *)) {
        return [SMAppService mainAppService].status == SMAppServiceStatusEnabled;
    }
    return NO;
}

static void setLaunchAtLogin(BOOL enable) {
    if (@available(macOS 13.0, *)) {
        NSError *err = nil;
        if (enable) {
            [[SMAppService mainAppService] registerAndReturnError:&err];
        } else {
            [[SMAppService mainAppService] unregisterAndReturnError:&err];
        }
        if (err) NSLog(@"SMAppService error: %@", err);
    }
}

// ── Mouse Movement ───────────────────────────────────────────────────────
static void jiggleMouse(int pixels) {
    int dx = (arc4random_uniform(pixels) + 1) * (arc4random_uniform(2) ? 1 : -1);
    int dy = (arc4random_uniform(pixels) + 1) * (arc4random_uniform(2) ? 1 : -1);
    CGEventRef dummy = CGEventCreate(NULL);
    CGPoint loc = CGEventGetLocation(dummy);
    CFRelease(dummy);
    CGPoint newPt = CGPointMake(loc.x + dx, loc.y + dy);
    CGEventRef move = CGEventCreateMouseEvent(NULL, kCGEventMouseMoved, newPt, kCGMouseButtonLeft);
    CGEventPost(kCGHIDEventTap, move);
    CFRelease(move);
}

// ── About Panel ──────────────────────────────────────────────────────────
static void showAbout(void) {
    NSAlert *alert = [[NSAlert alloc] init];
    alert.messageText = APP_NAME;
    alert.informativeText = [NSString stringWithFormat:
        @"Version %@\n\n"
        "Keeps your screen awake with imperceptible mouse movement.\n"
        "Runs quietly in the menu bar — no dock icon, no windows.\n\n"
        "Created by %@\n%@",
        APP_VERSION, APP_CREATOR, APP_WEBSITE];
    alert.alertStyle = NSAlertStyleInformational;
    [alert runModal];
}

// ── App Delegate ─────────────────────────────────────────────────────────
@interface AppDelegate : NSObject <NSApplicationDelegate>
@property (strong) NSStatusItem *statusItem;
@property (strong) NSDictionary *config;
@property (assign) BOOL running;
@property (assign) BOOL paused;
@end

@implementation AppDelegate

- (void)applicationDidFinishLaunching:(NSNotification *)notification {
    self.config = loadConfig();
    self.running = NO;
    self.paused = NO;

    self.statusItem = [[NSStatusBar systemStatusBar]
        statusItemWithLength:NSVariableStatusItemLength];

    // Try loading bundled icon, fallback to emoji
    NSImage *icon = [NSImage imageNamed:@"AppIcon"];
    if (icon) {
        icon.size = NSMakeSize(18, 18);
        icon.template = YES;
        self.statusItem.button.image = icon;
    } else {
        self.statusItem.button.title = @"🖱️";
    }

    [self rebuildMenu];

    // Apply launch-at-login setting
    BOOL storedLogin = [self.config[@"launchAtLogin"] boolValue];
    if (storedLogin != getLaunchAtLogin()) {
        setLaunchAtLogin(storedLogin);
    }

    if ([self.config[@"enabled"] boolValue]) {
        [self startJiggling];
    }
}

- (NSImage *)menuBarIcon {
    // Create a fallback programmatic icon
    NSImage *img = [[NSImage alloc] initWithSize:NSMakeSize(18, 18)];
    img.template = YES;
    [img lockFocus];
    [[NSColor controlTextColor] setFill];
    NSBezierPath *path = [NSBezierPath bezierPath];
    [path moveToPoint:NSMakePoint(3, 2)];
    [path lineToPoint:NSMakePoint(3, 13)];
    [path lineToPoint:NSMakePoint(7, 10)];
    [path lineToPoint:NSMakePoint(10, 15)];
    [path lineToPoint:NSMakePoint(13, 13)];
    [path lineToPoint:NSMakePoint(8, 8)];
    [path lineToPoint:NSMakePoint(12, 5)];
    [path closePath];
    [path fill];
    [img unlockFocus];
    return img;
}

- (void)rebuildMenu {
    NSMenu *menu = [[NSMenu alloc] init];
    menu.autoenablesItems = NO;

    // Pause / Resume
    NSString *pauseTitle = self.paused ? @"▶ Resume" : @"⏸ Pause";
    NSMenuItem *pauseItem = [[NSMenuItem alloc] initWithTitle:pauseTitle
        action:@selector(togglePause) keyEquivalent:@""];
    pauseItem.target = self;
    [menu addItem:pauseItem];
    [menu addItem:[NSMenuItem separatorItem]];

    // Interval
    NSMenuItem *intervalItem = [[NSMenuItem alloc] initWithTitle:@"Interval"
        action:NULL keyEquivalent:@""];
    NSMenu *intervalMenu = [[NSMenu alloc] init];
    int intervals[] = {30, 60, 120, 300, 600};
    NSString *labels[] = {@"30s", @"60s", @"2min", @"5min", @"10min"};
    int current = [self.config[@"interval"] intValue];
    for (int i = 0; i < 5; i++) {
        NSMenuItem *item = [[NSMenuItem alloc] initWithTitle:labels[i]
            action:@selector(setInterval:) keyEquivalent:@""];
        item.target = self; item.tag = intervals[i];
        item.state = (intervals[i] == current) ? NSControlStateValueOn : NSControlStateValueOff;
        [intervalMenu addItem:item];
    }
    intervalItem.submenu = intervalMenu;
    [menu addItem:intervalItem];

    // Pixels
    NSMenuItem *pixelsItem = [[NSMenuItem alloc] initWithTitle:@"Pixels"
        action:NULL keyEquivalent:@""];
    NSMenu *pixelsMenu = [[NSMenu alloc] init];
    int pxValues[] = {1, 2, 3, 5, 10};
    for (int i = 0; i < 5; i++) {
        NSString *title = [NSString stringWithFormat:@"%dpx", pxValues[i]];
        NSMenuItem *item = [[NSMenuItem alloc] initWithTitle:title
            action:@selector(setPixels:) keyEquivalent:@""];
        item.target = self; item.tag = pxValues[i];
        item.state = ([self.config[@"pixels"] intValue] == pxValues[i])
            ? NSControlStateValueOn : NSControlStateValueOff;
        [pixelsMenu addItem:item];
    }
    pixelsItem.submenu = pixelsMenu;
    [menu addItem:pixelsItem];

    [menu addItem:[NSMenuItem separatorItem]];

    // Launch at Login
    BOOL loginEnabled = getLaunchAtLogin();
    NSMenuItem *loginItem = [[NSMenuItem alloc] initWithTitle:@"Launch at Login"
        action:@selector(toggleLaunchAtLogin) keyEquivalent:@""];
    loginItem.target = self;
    loginItem.state = loginEnabled ? NSControlStateValueOn : NSControlStateValueOff;
    [menu addItem:loginItem];

    [menu addItem:[NSMenuItem separatorItem]];

    // Open Config
    NSMenuItem *configItem = [[NSMenuItem alloc] initWithTitle:@"Open Config File"
        action:@selector(openConfig) keyEquivalent:@""];
    configItem.target = self;
    [menu addItem:configItem];

    // About
    NSMenuItem *aboutItem = [[NSMenuItem alloc] initWithTitle:@"About Mouse Jiggler"
        action:@selector(showAbout) keyEquivalent:@""];
    aboutItem.target = self;
    [menu addItem:aboutItem];

    [menu addItem:[NSMenuItem separatorItem]];

    // Quit
    NSMenuItem *quitItem = [[NSMenuItem alloc] initWithTitle:@"Quit"
        action:@selector(terminate:) keyEquivalent:@"q"];
    [menu addItem:quitItem];

    self.statusItem.menu = menu;
}

- (void)startJiggling {
    if (self.running) return;
    self.running = YES; self.paused = NO;
    dispatch_async(dispatch_get_global_queue(DISPATCH_QUEUE_PRIORITY_DEFAULT, 0), ^{
        while (self.running) {
            if (!self.paused) {
                jiggleMouse([self.config[@"pixels"] intValue]);
            }
            [NSThread sleepForTimeInterval:[self.config[@"interval"] doubleValue]];
        }
    });
}

- (void)togglePause { self.paused = !self.paused; [self rebuildMenu]; }

- (void)setInterval:(NSMenuItem *)sender {
    NSMutableDictionary *cfg = [self.config mutableCopy];
    cfg[@"interval"] = @(sender.tag); self.config = cfg;
    saveConfig(cfg); [self rebuildMenu];
}

- (void)setPixels:(NSMenuItem *)sender {
    NSMutableDictionary *cfg = [self.config mutableCopy];
    cfg[@"pixels"] = @(sender.tag); self.config = cfg;
    saveConfig(cfg); [self rebuildMenu];
}

- (void)toggleLaunchAtLogin {
    BOOL current = getLaunchAtLogin();
    setLaunchAtLogin(!current);
    NSMutableDictionary *cfg = [self.config mutableCopy];
    cfg[@"launchAtLogin"] = @(!current);
    self.config = cfg;
    saveConfig(cfg);
    [self rebuildMenu];
}

- (void)openConfig {
    if (![[NSFileManager defaultManager] fileExistsAtPath:configPath()]) {
        saveConfig(self.config);
    }
    [[NSWorkspace sharedWorkspace] openFile:configPath()];
}

- (void)showAbout { showAbout(); }

@end

// ── Entry Point ──────────────────────────────────────────────────────────
int main(void) {
    @autoreleasepool {
        NSApplication *app = [NSApplication sharedApplication];
        AppDelegate *delegate = [[AppDelegate alloc] init];
        [app setDelegate:delegate];
        [app run];
    }
    return 0;
}
