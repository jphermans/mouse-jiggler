using Microsoft.Win32;
using System;
using System.Drawing;
using System.Drawing.Drawing2D;
using System.IO;
using System.Runtime.InteropServices;
using System.Text.Json;
using System.Threading;
using System.Windows.Forms;

namespace MouseJiggler;

// ── Win32 SendInput ──────────────────────────────────────────────────────
[StructLayout(LayoutKind.Sequential)]
struct MOUSEINPUT { public int dx; public int dy; public uint mouseData; public uint dwFlags; public uint time; public IntPtr dwExtraInfo; }

[StructLayout(LayoutKind.Explicit)]
struct INPUT_UNION { [FieldOffset(0)] public MOUSEINPUT mi; }

[StructLayout(LayoutKind.Sequential)]
struct INPUT { public uint type; public INPUT_UNION union; }

static class NativeMethods
{
    public const uint INPUT_MOUSE = 0;
    public const uint MOUSEEVENTF_MOVE = 0x0001;

    [DllImport("user32.dll")]
    public static extern uint SendInput(uint nInputs, INPUT[] pInputs, int cbSize);

    [DllImport("kernel32.dll")]
    public static extern IntPtr CreateMutex(IntPtr lpMutexAttributes, bool bInitialOwner, string lpName);

    [DllImport("kernel32.dll")]
    public static extern int GetLastError();
}

// ── Config ───────────────────────────────────────────────────────────────
record Config(int Interval = 60, int Pixels = 3, bool Enabled = true, bool LaunchAtStartup = false);

static class ConfigManager
{
    static readonly string Dir = Path.Combine(
        Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData), "Mouse Jiggler");
    static readonly string FilePath = Path.Combine(Dir, "config.json");

    public static Config Load()
    {
        try
        {
            if (File.Exists(FilePath))
                return JsonSerializer.Deserialize<Config>(File.ReadAllText(FilePath)) ?? new();
        }
        catch { }
        return new();
    }

    public static void Save(Config cfg)
    {
        Directory.CreateDirectory(Dir);
        File.WriteAllText(FilePath, JsonSerializer.Serialize(cfg, new JsonSerializerOptions { WriteIndented = true }));
    }
}

// ── Launch at Startup (Registry) ─────────────────────────────────────────
static class StartupManager
{
    const string RunKey = @"SOFTWARE\Microsoft\Windows\CurrentVersion\Run";
    const string AppName = "MouseJiggler";

    public static bool IsEnabled()
    {
        using var key = Registry.CurrentUser.OpenSubKey(RunKey);
        return key?.GetValue(AppName) != null;
    }

    public static void SetEnabled(bool enable)
    {
        using var key = Registry.CurrentUser.OpenSubKey(RunKey, true);
        if (key == null) return;
        if (enable)
            key.SetValue(AppName, $"\"{Application.ExecutablePath}\"");
        else
            key.DeleteValue(AppName, false);
    }
}

// ── Settings Form ────────────────────────────────────────────────────────
class SettingsForm : Form
{
    readonly TrackBar intervalBar = new() { Minimum = 5, Maximum = 600, TickFrequency = 30, Width = 340 };
    readonly TrackBar pixelsBar = new() { Minimum = 1, Maximum = 10, TickFrequency = 1, Width = 340 };
    readonly CheckBox enabledCheck = new() { Text = "Enable jiggling" };
    readonly CheckBox startupCheck = new() { Text = "Launch at Windows startup" };
    readonly Label intervalLabel = new(), pixelsLabel = new();
    readonly Label titleLabel = new();
    readonly Button saveBtn = new() { Text = "Save", Width = 80, Height = 30 };
    readonly Button cancelBtn = new() { Text = "Cancel", Width = 80, Height = 30 };
    readonly PictureBox iconBox = new() { Size = new Size(48, 48) };

    public Config Result { get; private set; }
    readonly Color bg = Color.FromArgb(32, 32, 36);
    readonly Color fg = Color.FromArgb(220, 220, 228);
    readonly Color accent = Color.FromArgb(76, 175, 80);
    readonly Color muted = Color.FromArgb(140, 145, 155);

    public SettingsForm(Config current)
    {
        Result = current;
        Text = "Mouse Jiggler — Settings";
        FormBorderStyle = FormBorderStyle.FixedDialog;
        MaximizeBox = false; MinimizeBox = false;
        StartPosition = FormStartPosition.CenterScreen;
        Size = new Size(460, 360);
        BackColor = bg;
        ForeColor = fg;

        // Icon
        iconBox.Image = SystemIcons.Application.ToBitmap();
        iconBox.SizeMode = PictureBoxSizeMode.Zoom;
        iconBox.Location = new Point(20, 20);

        // Title
        titleLabel.Text = "Mouse Jiggler";
        titleLabel.Font = new Font("Segoe UI", 16, FontStyle.Bold);
        titleLabel.ForeColor = accent;
        titleLabel.Location = new Point(80, 22);
        titleLabel.AutoSize = true;

        var subtitle = new Label
        {
            Text = "Keep your screen awake",
            Font = new Font("Segoe UI", 9),
            ForeColor = muted,
            Location = new Point(82, 50),
            AutoSize = true
        };

        // Separator
        var sep = new Panel { Height = 1, Width = 410, Location = new Point(20, 78), BackColor = Color.FromArgb(60, 60, 68) };

        // Enable checkbox
        enabledCheck.Checked = current.Enabled;
        enabledCheck.Location = new Point(20, 95);
        enabledCheck.BackColor = bg; enabledCheck.ForeColor = fg;
        enabledCheck.Font = new Font("Segoe UI", 10);

        // Interval
        intervalBar.Value = current.Interval;
        intervalLabel.Text = $"Interval: {current.Interval}s";
        intervalLabel.Location = new Point(20, 125);
        intervalLabel.ForeColor = fg;
        intervalLabel.Font = new Font("Segoe UI", 9);
        intervalBar.Location = new Point(20, 148);
        intervalBar.Scroll += (_, _) => intervalLabel.Text = $"Interval: {intervalBar.Value}s";

        // Pixels
        pixelsBar.Value = current.Pixels;
        pixelsLabel.Text = $"Max pixels per move: {current.Pixels}px";
        pixelsLabel.Location = new Point(20, 190);
        pixelsLabel.ForeColor = fg;
        pixelsLabel.Font = new Font("Segoe UI", 9);
        pixelsBar.Location = new Point(20, 213);
        pixelsBar.Scroll += (_, _) => pixelsLabel.Text = $"Max pixels per move: {pixelsBar.Value}px";

        // Launch at startup
        startupCheck.Checked = StartupManager.IsEnabled();
        startupCheck.Location = new Point(20, 260);
        startupCheck.BackColor = bg; startupCheck.ForeColor = fg;
        startupCheck.Font = new Font("Segoe UI", 10);

        // Buttons
        saveBtn.Location = new Point(260, 275);
        saveBtn.FlatStyle = FlatStyle.Flat;
        saveBtn.BackColor = accent; saveBtn.ForeColor = Color.White;
        saveBtn.FlatAppearance.BorderSize = 0;
        saveBtn.Click += (_, _) => {
            Result = new(intervalBar.Value, pixelsBar.Value, enabledCheck.Checked, Result.LaunchAtStartup);
            StartupManager.SetEnabled(startupCheck.Checked);
            DialogResult = DialogResult.OK; Close();
        };

        cancelBtn.Location = new Point(350, 275);
        cancelBtn.FlatStyle = FlatStyle.Flat;
        cancelBtn.BackColor = Color.FromArgb(60, 60, 68);
        cancelBtn.ForeColor = fg;
        cancelBtn.Click += (_, _) => { DialogResult = DialogResult.Cancel; Close(); };

        Controls.AddRange([
            iconBox, titleLabel, subtitle, sep,
            enabledCheck, intervalLabel, intervalBar, pixelsLabel, pixelsBar,
            startupCheck, saveBtn, cancelBtn
        ]);
    }
}

// ── About Dialog ─────────────────────────────────────────────────────────
static class AboutDialog
{
    public static void Show()
    {
        var form = new Form
        {
            Text = "About Mouse Jiggler",
            FormBorderStyle = FormBorderStyle.FixedDialog,
            MaximizeBox = false, MinimizeBox = false,
            StartPosition = FormStartPosition.CenterScreen,
            Size = new Size(380, 260),
            BackColor = Color.FromArgb(32, 32, 36),
            ForeColor = Color.FromArgb(220, 220, 228)
        };

        var icon = new PictureBox
        {
            Image = SystemIcons.Application.ToBitmap(),
            SizeMode = PictureBoxSizeMode.Zoom,
            Size = new Size(64, 64),
            Location = new Point(30, 25)
        };

        var title = new Label
        {
            Text = "Mouse Jiggler",
            Font = new Font("Segoe UI", 14, FontStyle.Bold),
            ForeColor = Color.FromArgb(76, 175, 80),
            Location = new Point(110, 20),
            AutoSize = true
        };

        var version = new Label
        {
            Text = "Version 1.0.0",
            Font = new Font("Segoe UI", 9),
            ForeColor = Color.FromArgb(140, 145, 155),
            Location = new Point(112, 48),
            AutoSize = true
        };

        var desc = new Label
        {
            Text = "Keeps your screen awake with imperceptible\nmouse movement from the system tray.\n\nNo services. No registry keys. No admin rights.\nUses Win32 SendInput — indistinguishable\nfrom real hardware input.",
            Font = new Font("Segoe UI", 9),
            ForeColor = Color.FromArgb(180, 185, 195),
            Location = new Point(30, 100),
            AutoSize = true
        };

        var creator = new Label
        {
            Text = "Created by Jean-Pierre Hermans\ngithub.com/jphermans/mouse-jiggler",
            Font = new Font("Segoe UI", 8),
            ForeColor = Color.FromArgb(120, 125, 135),
            Location = new Point(30, 185),
            AutoSize = true
        };

        var okBtn = new Button
        {
            Text = "OK",
            Width = 80,
            Location = new Point(275, 185),
            FlatStyle = FlatStyle.Flat,
            BackColor = Color.FromArgb(76, 175, 80),
            ForeColor = Color.White
        };
        okBtn.FlatAppearance.BorderSize = 0;
        okBtn.Click += (_, _) => form.Close();

        form.Controls.AddRange([icon, title, version, desc, creator, okBtn]);
        form.ShowDialog();
    }
}

// ── Main App ─────────────────────────────────────────────────────────────
class JigglerApp : ApplicationContext
{
    readonly NotifyIcon trayIcon;
    Config config;
    bool running, paused;
    Thread? jiggleThread;
    readonly Random rng = new();

    public JigglerApp()
    {
        config = ConfigManager.Load();

        trayIcon = new NotifyIcon
        {
            Icon = MakeIcon(),
            Text = "Mouse Jiggler",
            Visible = true,
            ContextMenuStrip = BuildMenu()
        };

        trayIcon.DoubleClick += (_, _) => OpenSettings();

        if (config.Enabled) StartJiggling();
    }

    Icon MakeIcon()
    {
        // Use embedded icon from resources, fall back to generated
        try
        {
            using var stream = GetType().Assembly.GetManifestResourceStream("MouseJiggler.mouse_jiggler.ico");
            if (stream != null) return new Icon(stream);
        }
        catch { }

        return GenerateIcon();
    }

    static Icon GenerateIcon()
    {
        var bmp = new Bitmap(32, 32);
        using var g = Graphics.FromImage(bmp);
        g.Clear(Color.Transparent);
        g.SmoothingMode = SmoothingMode.AntiAlias;

        using var brush = new SolidBrush(Color.FromArgb(76, 175, 80));
        g.FillEllipse(brush, 1, 1, 30, 30);

        using var cursorBrush = new SolidBrush(Color.White);
        var pts = new Point[] { new(7,24), new(10,18), new(15,22), new(20,14), new(18,9), new(25,7) };
        g.FillPolygon(cursorBrush, pts, FillMode.Winding);

        return Icon.FromHandle(bmp.GetHicon());
    }

    ContextMenuStrip BuildMenu()
    {
        var menu = new ContextMenuStrip();
        menu.Renderer = new DarkToolStripRenderer();

        var pauseItem = menu.Items.Add(paused ? "▶ Resume" : "⏸ Pause", null, (_, _) =>
        {
            paused = !paused;
            trayIcon.Text = paused ? "Mouse Jiggler (Paused)" : "Mouse Jiggler";
            trayIcon.ContextMenuStrip = BuildMenu();
        });
        pauseItem.Font = new Font("Segoe UI", 9, FontStyle.Bold);

        menu.Items.Add(new ToolStripSeparator());

        var intervalItem = new ToolStripMenuItem("Interval");
        foreach (var secs in new[] { 30, 60, 120, 300, 600 })
        {
            var label = secs < 120 ? $"{secs}s" : $"{secs / 60}min";
            var item = intervalItem.DropDownItems.Add(label, null, (_, _) =>
            {
                config = config with { Interval = secs };
                ConfigManager.Save(config);
                trayIcon.ContextMenuStrip = BuildMenu();
            });
            if (secs == config.Interval) item.Font = new Font(item.Font!, FontStyle.Bold);
        }
        menu.Items.Add(intervalItem);

        var pixelsItem = new ToolStripMenuItem("Pixels");
        foreach (var px in new[] { 1, 2, 3, 5, 10 })
        {
            var item = pixelsItem.DropDownItems.Add($"{px}px", null, (_, _) =>
            {
                config = config with { Pixels = px };
                ConfigManager.Save(config);
                trayIcon.ContextMenuStrip = BuildMenu();
            });
            if (px == config.Pixels) item.Font = new Font(item.Font!, FontStyle.Bold);
        }
        menu.Items.Add(pixelsItem);

        menu.Items.Add(new ToolStripSeparator());

        var startupItem = menu.Items.Add("Launch at Startup", null, (_, _) =>
        {
            var enabled = !StartupManager.IsEnabled();
            StartupManager.SetEnabled(enabled);
            trayIcon.ContextMenuStrip = BuildMenu();
        });
        startupItem.Font = new Font(startupItem.Font!, StartupManager.IsEnabled() ? FontStyle.Bold : FontStyle.Regular);

        menu.Items.Add(new ToolStripSeparator());

        menu.Items.Add("Open Config Folder", null, (_, _) =>
        {
            var folder = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData), "Mouse Jiggler");
            Directory.CreateDirectory(folder);
            System.Diagnostics.Process.Start("explorer.exe", folder);
        });

        menu.Items.Add("About Mouse Jiggler", null, (_, _) => AboutDialog.Show());

        menu.Items.Add(new ToolStripSeparator());

        var quitItem = menu.Items.Add("Exit", null, (_, _) =>
        {
            running = false;
            trayIcon.Visible = false;
            Application.Exit();
        });
        quitItem.Font = new Font("Segoe UI", 9);

        return menu;
    }

    void OpenSettings()
    {
        using var form = new SettingsForm(config);
        if (form.ShowDialog() == DialogResult.OK)
        {
            config = form.Result;
            ConfigManager.Save(config);
            if (!config.Enabled) paused = true;
            else if (paused && config.Enabled) paused = false;
            trayIcon.ContextMenuStrip = BuildMenu();
        }
    }

    void StartJiggling()
    {
        if (running) return;
        running = true; paused = false;
        jiggleThread = new Thread(() =>
        {
            while (running)
            {
                if (!paused) Jiggle();
                Thread.Sleep(config.Interval * 1000);
            }
        })
        { IsBackground = true };
        jiggleThread.Start();
    }

    void Jiggle()
    {
        var dx = (rng.Next(1, config.Pixels + 1)) * (rng.Next(2) == 0 ? -1 : 1);
        var dy = (rng.Next(1, config.Pixels + 1)) * (rng.Next(2) == 0 ? -1 : 1);
        var input = new INPUT
        {
            type = NativeMethods.INPUT_MOUSE,
            union = new INPUT_UNION { mi = new MOUSEINPUT { dx = dx, dy = dy, dwFlags = NativeMethods.MOUSEEVENTF_MOVE } }
        };
        NativeMethods.SendInput(1, [input], Marshal.SizeOf<INPUT>());
    }
}

// ── Dark-themed menu renderer ────────────────────────────────────────────
class DarkToolStripRenderer : ToolStripProfessionalRenderer
{
    public DarkToolStripRenderer() : base(new DarkColorTable()) { }

    protected override void OnRenderItemText(ToolStripItemTextRenderEventArgs e)
    {
        // Force light text on dark background
        e.TextColor = e.Item.Selected
            ? Color.White
            : Color.FromArgb(220, 220, 228);
        base.OnRenderItemText(e);
    }

    protected override void OnRenderArrow(ToolStripArrowRenderEventArgs e)
    {
        e.ArrowColor = Color.FromArgb(180, 180, 190);
        base.OnRenderArrow(e);
    }

    class DarkColorTable : ProfessionalColorTable
    {
        public override Color MenuItemBorder => Color.Transparent;
        public override Color MenuItemSelected => Color.FromArgb(76, 175, 80);
        public override Color MenuItemSelectedGradientBegin => Color.FromArgb(60, 60, 68);
        public override Color MenuItemSelectedGradientEnd => Color.FromArgb(60, 60, 68);
        public override Color ToolStripDropDownBackground => Color.FromArgb(40, 40, 46);
        public override Color ImageMarginGradientBegin => Color.FromArgb(40, 40, 46);
        public override Color ImageMarginGradientMiddle => Color.FromArgb(40, 40, 46);
        public override Color ImageMarginGradientEnd => Color.FromArgb(40, 40, 46);
        public override Color MenuBorder => Color.FromArgb(60, 60, 68);
        public override Color SeparatorDark => Color.FromArgb(55, 55, 62);
        public override Color SeparatorLight => Color.FromArgb(55, 55, 62);
        public override Color MenuItemPressedGradientBegin => Color.FromArgb(50, 50, 56);
        public override Color MenuItemPressedGradientEnd => Color.FromArgb(50, 50, 56);
    }
}

// ── Entry Point ──────────────────────────────────────────────────────────
class Program
{
    [STAThread]
    static void Main()
    {
        var mutex = NativeMethods.CreateMutex(IntPtr.Zero, true, "Global\\MouseJigglerSingleInstance");
        if (NativeMethods.GetLastError() == 183)
        {
            MessageBox.Show("Mouse Jiggler is already running.\nCheck your system tray.",
                "Mouse Jiggler", MessageBoxButtons.OK, MessageBoxIcon.Information);
            return;
        }

        Application.EnableVisualStyles();
        Application.SetCompatibleTextRenderingDefault(false);
        Application.Run(new JigglerApp());
        GC.KeepAlive(mutex);
    }
}
