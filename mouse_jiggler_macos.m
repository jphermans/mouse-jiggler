#import <Cocoa/Cocoa.h>
#import <CoreGraphics/CoreGraphics.h>

// ── Configuration ────────────────────────────────────────────────────────
static NSString *APP_NAME = @"Mouse Jiggler";

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
    if (!data) return @{@"interval": @60, @"pixels": @3, @"enabled": @YES};
    return [NSJSONSerialization JSONObjectWithData:data options:0 error:nil]
        ?: @{@"interval": @60, @"pixels": @3, @"enabled": @YES};
}

static void saveConfig(NSDictionary *config) {
    NSData *data = [NSJSONSerialization dataWithJSONObject:config options:NSJSONWritingPrettyPrinted error:nil];
    [data writeToFile:configPath() atomically:YES];
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
    self.statusItem.button.title = @"🖱️";

    [self rebuildMenu];

    if ([self.config[@"enabled"] boolValue]) {
        [self startJiggling];
    }
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
        item.target = self;
        item.tag = intervals[i];
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
        item.target = self;
        item.tag = pxValues[i];
        item.state = ([self.config[@"pixels"] intValue] == pxValues[i])
            ? NSControlStateValueOn : NSControlStateValueOff;
        [pixelsMenu addItem:item];
    }
    pixelsItem.submenu = pixelsMenu;
    [menu addItem:pixelsItem];

    [menu addItem:[NSMenuItem separatorItem]];

    // Config
    NSMenuItem *configItem = [[NSMenuItem alloc] initWithTitle:@"Open Config File"
        action:@selector(openConfig) keyEquivalent:@""];
    configItem.target = self;
    [menu addItem:configItem];

    [menu addItem:[NSMenuItem separatorItem]];

    // Quit
    NSMenuItem *quitItem = [[NSMenuItem alloc] initWithTitle:@"Quit"
        action:@selector(terminate:) keyEquivalent:@"q"];
    [menu addItem:quitItem];

    self.statusItem.menu = menu;
}

- (void)startJiggling {
    if (self.running) return;
    self.running = YES;
    self.paused = NO;
    dispatch_async(dispatch_get_global_queue(DISPATCH_QUEUE_PRIORITY_DEFAULT, 0), ^{
        while (self.running) {
            if (!self.paused) {
                jiggleMouse([self.config[@"pixels"] intValue]);
            }
            [NSThread sleepForTimeInterval:[self.config[@"interval"] doubleValue]];
        }
    });
}

- (void)togglePause {
    self.paused = !self.paused;
    [self rebuildMenu];
}

- (void)setInterval:(NSMenuItem *)sender {
    NSMutableDictionary *cfg = [self.config mutableCopy];
    cfg[@"interval"] = @(sender.tag);
    self.config = cfg;
    saveConfig(cfg);
    [self rebuildMenu];
}

- (void)setPixels:(NSMenuItem *)sender {
    NSMutableDictionary *cfg = [self.config mutableCopy];
    cfg[@"pixels"] = @(sender.tag);
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
