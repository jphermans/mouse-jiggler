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
    [DllImport("user32.dll")] public static extern uint SendInput(uint nInputs, INPUT[] pInputs, int cbSize);
    [DllImport("kernel32.dll")] public static extern IntPtr CreateMutex(IntPtr lpMutexAttributes, bool bInitialOwner, string lpName);
    [DllImport("kernel32.dll")] public static extern int GetLastError();
}

// ── Config ───────────────────────────────────────────────────────────────
record Config(int Interval = 60, int Pixels = 3, bool Enabled = true, bool DarkMode = true);

static class ConfigManager
{
    static readonly string Dir = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData), "Mouse Jiggler");
    static readonly string FilePath = Path.Combine(Dir, "config.json");

    public static Config Load()
    {
        try { if (File.Exists(FilePath)) return JsonSerializer.Deserialize<Config>(File.ReadAllText(FilePath)) ?? new(); }
        catch { }
        return new();
    }

    public static void Save(Config cfg)
    {
        Directory.CreateDirectory(Dir);
        File.WriteAllText(FilePath, JsonSerializer.Serialize(cfg, new JsonSerializerOptions { WriteIndented = true }));
    }
}

// ── Startup ──────────────────────────────────────────────────────────────
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
        if (enable) key.SetValue(AppName, $"\"{Application.ExecutablePath}\"");
        else key.DeleteValue(AppName, false);
    }
}

// ── Theme ────────────────────────────────────────────────────────────────
static class Theme
{
    public static Color Bg(bool dark) => dark ? Color.FromArgb(32, 32, 36) : SystemColors.Control;
    public static Color Fg(bool dark) => dark ? Color.FromArgb(220, 220, 228) : SystemColors.ControlText;
    public static Color Accent(bool _) => Color.FromArgb(76, 175, 80);
    public static Color Muted(bool dark) => dark ? Color.FromArgb(140, 145, 155) : Color.FromArgb(100, 100, 110);
    public static Color Sep(bool dark) => dark ? Color.FromArgb(60, 60, 68) : Color.FromArgb(220, 220, 225);
    public static Color BtnBg(bool dark) => dark ? Color.FromArgb(60, 60, 68) : Color.FromArgb(230, 230, 235);
    public static Color BtnFg(bool dark) => dark ? Color.FromArgb(220, 220, 228) : SystemColors.ControlText;

    public static Color TrayText(bool dark) => dark ? Color.FromArgb(220, 220, 228) : SystemColors.ControlText;
    public static Color TrayBg(bool dark) => dark ? Color.FromArgb(40, 40, 46) : SystemColors.ControlLightLight;
    public static Color TrayHover(bool dark) => dark ? Color.FromArgb(60, 60, 68) : Color.FromArgb(230, 230, 235);
    public static Color TrayBorder(bool dark) => dark ? Color.FromArgb(60, 60, 68) : Color.FromArgb(200, 200, 210);
    public static Color TraySep(bool dark) => dark ? Color.FromArgb(55, 55, 62) : Color.FromArgb(220, 220, 225);

    public static void ApplyToForm(Form form, bool dark)
    {
        form.BackColor = Bg(dark);
        form.ForeColor = Fg(dark);
        ApplyToControls(form.Controls, dark);
    }

    static void ApplyToControls(Control.ControlCollection controls, bool dark)
    {
        foreach (Control c in controls)
        {
            if (c is Label || c is CheckBox || c is GroupBox)
            {
                c.BackColor = Bg(dark);
                c.ForeColor = Fg(dark);
            }
            if (c.HasChildren) ApplyToControls(c.Controls, dark);
        }
    }
}

// ── Settings Form ────────────────────────────────────────────────────────
class SettingsForm : Form
{
    readonly TrackBar intervalBar = new() { Minimum = 5, Maximum = 600, TickFrequency = 30, Width = 340 };
    readonly TrackBar pixelsBar = new() { Minimum = 1, Maximum = 10, TickFrequency = 1, Width = 340 };
    readonly CheckBox enabledCheck = new() { Text = "Enable jiggling" };
    readonly CheckBox startupCheck = new() { Text = "Launch at Windows startup" };
    readonly CheckBox darkModeCheck = new() { Text = "Dark mode" };
    readonly Label intervalLabel = new(), pixelsLabel = new(), titleLabel = new();
    readonly Button saveBtn = new() { Text = "Save", Width = 80, Height = 30 };
    readonly Button cancelBtn = new() { Text = "Cancel", Width = 80, Height = 30 };
    readonly PictureBox iconBox = new() { Size = new Size(48, 48) };

    public Config Result { get; private set; }
    readonly bool dark;

    public SettingsForm(Config current)
    {
        Result = current;
        dark = current.DarkMode;
        Text = "Mouse Jiggler — Settings";
        FormBorderStyle = FormBorderStyle.FixedDialog;
        MaximizeBox = false; MinimizeBox = false;
        StartPosition = FormStartPosition.CenterScreen;
        Size = new Size(460, 390);
        Theme.ApplyToForm(this, dark);
        if (dark) ForeColor = Theme.Fg(true);

        iconBox.Image = SystemIcons.Application.ToBitmap();
        iconBox.SizeMode = PictureBoxSizeMode.Zoom;
        iconBox.Location = new Point(20, 20);

        titleLabel.Text = "Mouse Jiggler";
        titleLabel.Font = new Font("Segoe UI", 16, FontStyle.Bold);
        titleLabel.ForeColor = Theme.Accent(dark);
        titleLabel.Location = new Point(80, 22);
        titleLabel.AutoSize = true;

        var subtitle = new Label { Text = "Keep your screen awake", Font = new Font("Segoe UI", 9), Location = new Point(82, 50), AutoSize = true, ForeColor = Theme.Muted(dark) };
        var sep = new Panel { Height = 1, Width = 410, Location = new Point(20, 78), BackColor = Theme.Sep(dark) };

        enabledCheck.Checked = current.Enabled;
        enabledCheck.Location = new Point(20, 95);
        enabledCheck.BackColor = Theme.Bg(dark); enabledCheck.ForeColor = Theme.Fg(dark);
        enabledCheck.Font = new Font("Segoe UI", 10);

        intervalBar.Value = current.Interval;
        intervalLabel.Text = $"Interval: {current.Interval}s";
        intervalLabel.Location = new Point(20, 125);
        intervalLabel.ForeColor = Theme.Fg(dark); intervalLabel.Font = new Font("Segoe UI", 9);
        intervalBar.Location = new Point(20, 148);
        intervalBar.Scroll += (_, _) => intervalLabel.Text = $"Interval: {intervalBar.Value}s";

        pixelsBar.Value = current.Pixels;
        pixelsLabel.Text = $"Max pixels per move: {current.Pixels}px";
        pixelsLabel.Location = new Point(20, 190);
        pixelsLabel.ForeColor = Theme.Fg(dark); pixelsLabel.Font = new Font("Segoe UI", 9);
        pixelsBar.Location = new Point(20, 213);
        pixelsBar.Scroll += (_, _) => pixelsLabel.Text = $"Max pixels per move: {pixelsBar.Value}px";

        darkModeCheck.Checked = dark;
        darkModeCheck.Location = new Point(20, 260);
        darkModeCheck.BackColor = Theme.Bg(dark); darkModeCheck.ForeColor = Theme.Fg(dark);
        darkModeCheck.Font = new Font("Segoe UI", 10);

        startupCheck.Checked = StartupManager.IsEnabled();
        startupCheck.Location = new Point(20, 290);
        startupCheck.BackColor = Theme.Bg(dark); startupCheck.ForeColor = Theme.Fg(dark);
        startupCheck.Font = new Font("Segoe UI", 10);

        saveBtn.Location = new Point(260, 310);
        saveBtn.FlatStyle = FlatStyle.Flat; saveBtn.BackColor = Theme.Accent(dark); saveBtn.ForeColor = Color.White;
        saveBtn.FlatAppearance.BorderSize = 0;
        saveBtn.Click += (_, _) => {
            Result = new(intervalBar.Value, pixelsBar.Value, enabledCheck.Checked, darkModeCheck.Checked);
            StartupManager.SetEnabled(startupCheck.Checked);
            DialogResult = DialogResult.OK; Close();
        };

        cancelBtn.Location = new Point(350, 310);
        cancelBtn.FlatStyle = FlatStyle.Flat; cancelBtn.BackColor = Theme.BtnBg(dark); cancelBtn.ForeColor = Theme.BtnFg(dark);
        cancelBtn.Click += (_, _) => { DialogResult = DialogResult.Cancel; Close(); };

        Controls.AddRange([iconBox, titleLabel, subtitle, sep, enabledCheck, intervalLabel, intervalBar, pixelsLabel, pixelsBar, darkModeCheck, startupCheck, saveBtn, cancelBtn]);
    }
}

// ── About ────────────────────────────────────────────────────────────────
static class AboutDialog
{
    public static void Show()
    {
        var dark = ConfigManager.Load().DarkMode;
        var form = new Form
        {
            Text = "About Mouse Jiggler", FormBorderStyle = FormBorderStyle.FixedDialog,
            MaximizeBox = false, MinimizeBox = false, StartPosition = FormStartPosition.CenterScreen,
            Size = new Size(380, 260)
        };
        Theme.ApplyToForm(form, dark);

        var icon = new PictureBox { Image = SystemIcons.Application.ToBitmap(), SizeMode = PictureBoxSizeMode.Zoom, Size = new Size(64, 64), Location = new Point(30, 25) };
        var title = new Label { Text = "Mouse Jiggler", Font = new Font("Segoe UI", 14, FontStyle.Bold), ForeColor = Theme.Accent(dark), Location = new Point(110, 20), AutoSize = true };
        var version = new Label { Text = "Version 1.0.0", Font = new Font("Segoe UI", 9), ForeColor = Theme.Muted(dark), Location = new Point(112, 48), AutoSize = true };
        var desc = new Label { Text = "Keeps your screen awake with imperceptible\nmouse movement from the system tray.\n\nNo services. No registry keys. No admin rights.\nUses Win32 SendInput — indistinguishable\nfrom real hardware input.", Font = new Font("Segoe UI", 9), ForeColor = Theme.Fg(dark), Location = new Point(30, 100), AutoSize = true };
        var creator = new Label { Text = "Created by Jean-Pierre Hermans\ngithub.com/jphermans/mouse-jiggler", Font = new Font("Segoe UI", 8), ForeColor = Theme.Muted(dark), Location = new Point(30, 185), AutoSize = true };
        var okBtn = new Button { Text = "OK", Width = 80, Location = new Point(275, 185), FlatStyle = FlatStyle.Flat, BackColor = Theme.Accent(dark), ForeColor = Color.White };
        okBtn.FlatAppearance.BorderSize = 0;
        okBtn.Click += (_, _) => form.Close();

        form.Controls.AddRange([icon, title, version, desc, creator, okBtn]);
        form.ShowDialog();
    }
}

// ── Theme-aware menu renderer ────────────────────────────────────────────
class ThemedRenderer : ToolStripProfessionalRenderer
{
    readonly bool dark;
    public ThemedRenderer(bool dark) : base(new ThemedColorTable(dark)) { this.dark = dark; }

    protected override void OnRenderItemText(ToolStripItemTextRenderEventArgs e)
    {
        e.TextColor = e.Item.Selected ? Theme.Accent(dark) : Theme.Fg(dark);
        base.OnRenderItemText(e);
    }

    protected override void OnRenderArrow(ToolStripArrowRenderEventArgs e)
    {
        e.ArrowColor = Theme.Fg(dark);
        base.OnRenderArrow(e);
    }

    class ThemedColorTable : ProfessionalColorTable
    {
        readonly bool dark;
        public ThemedColorTable(bool dark) => this.dark = dark;
        public override Color MenuItemBorder => Color.Transparent;
        public override Color MenuItemSelected => Theme.Accent(dark);
        public override Color MenuItemSelectedGradientBegin => Theme.TrayHover(dark);
        public override Color MenuItemSelectedGradientEnd => Theme.TrayHover(dark);
        public override Color ToolStripDropDownBackground => Theme.TrayBg(dark);
        public override Color ImageMarginGradientBegin => Theme.TrayBg(dark);
        public override Color ImageMarginGradientMiddle => Theme.TrayBg(dark);
        public override Color ImageMarginGradientEnd => Theme.TrayBg(dark);
        public override Color MenuBorder => Theme.TrayBorder(dark);
        public override Color SeparatorDark => Theme.TraySep(dark);
        public override Color SeparatorLight => Theme.TraySep(dark);
        public override Color MenuItemPressedGradientBegin => Theme.TrayHover(dark);
        public override Color MenuItemPressedGradientEnd => Theme.TrayHover(dark);
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
        trayIcon = new NotifyIcon { Icon = MakeIcon(), Text = "Mouse Jiggler", Visible = true, ContextMenuStrip = BuildMenu() };
        trayIcon.DoubleClick += (_, _) => OpenSettings();
        if (config.Enabled) StartJiggling();
    }

    Icon MakeIcon()
    {
        try { using var s = GetType().Assembly.GetManifestResourceStream("MouseJiggler.mouse_jiggler.ico"); if (s != null) return new Icon(s); } catch { }
        return GenerateIcon();
    }

    static Icon GenerateIcon()
    {
        var bmp = new Bitmap(32, 32);
        using var g = Graphics.FromImage(bmp);
        g.Clear(Color.Transparent); g.SmoothingMode = SmoothingMode.AntiAlias;
        using (var b = new SolidBrush(Color.FromArgb(76, 175, 80))) g.FillEllipse(b, 1, 1, 30, 30);
        using (var b = new SolidBrush(Color.White)) g.FillPolygon(b, new Point[] { new(7, 24), new(10, 18), new(15, 22), new(20, 14), new(18, 9), new(25, 7) }, FillMode.Winding);
        return Icon.FromHandle(bmp.GetHicon());
    }

    ContextMenuStrip BuildMenu()
    {
        var dark = config.DarkMode;
        var menu = new ContextMenuStrip { Renderer = new ThemedRenderer(dark) };

        menu.Items.Add(paused ? "▶ Resume" : "⏸ Pause", null, (_, _) =>
        {
            paused = !paused;
            trayIcon.Text = paused ? "Mouse Jiggler (Paused)" : "Mouse Jiggler";
            trayIcon.ContextMenuStrip = BuildMenu();
        });

        menu.Items.Add(new ToolStripSeparator());

        var iv = new ToolStripMenuItem("Interval");
        foreach (var s in new[] { 30, 60, 120, 300, 600 })
        {
            var l = s < 120 ? $"{s}s" : $"{s / 60}min";
            var it = iv.DropDownItems.Add(l, null, (_, _) => { config = config with { Interval = s }; ConfigManager.Save(config); trayIcon.ContextMenuStrip = BuildMenu(); });
            if (s == config.Interval) it.Font = new Font(it.Font!, FontStyle.Bold);
        }
        menu.Items.Add(iv);

        var px = new ToolStripMenuItem("Pixels");
        foreach (var v in new[] { 1, 2, 3, 5, 10 })
        {
            var it = px.DropDownItems.Add($"{v}px", null, (_, _) => { config = config with { Pixels = v }; ConfigManager.Save(config); trayIcon.ContextMenuStrip = BuildMenu(); });
            if (v == config.Pixels) it.Font = new Font(it.Font!, FontStyle.Bold);
        }
        menu.Items.Add(px);

        menu.Items.Add(new ToolStripSeparator());

        // Dark/Light toggle
        var themeItem = menu.Items.Add(dark ? "☀  Light Mode" : "🌙  Dark Mode", null, (_, _) =>
        {
            config = config with { DarkMode = !config.DarkMode };
            ConfigManager.Save(config);
            trayIcon.ContextMenuStrip = BuildMenu();
        });

        menu.Items.Add("Launch at Startup", null, (_, _) =>
        {
            StartupManager.SetEnabled(!StartupManager.IsEnabled());
            trayIcon.ContextMenuStrip = BuildMenu();
        })!.Font = new Font(SystemFonts.MenuFont, StartupManager.IsEnabled() ? FontStyle.Bold : FontStyle.Regular);

        menu.Items.Add(new ToolStripSeparator());

        menu.Items.Add("Open Config Folder", null, (_, _) =>
        {
            var f = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData), "Mouse Jiggler");
            Directory.CreateDirectory(f);
            System.Diagnostics.Process.Start("explorer.exe", f);
        });

        menu.Items.Add("About Mouse Jiggler", null, (_, _) => AboutDialog.Show());

        menu.Items.Add(new ToolStripSeparator());
        menu.Items.Add("Exit", null, (_, _) => { running = false; trayIcon.Visible = false; Application.Exit(); });

        return menu;
    }

    void OpenSettings()
    {
        using var f = new SettingsForm(config);
        if (f.ShowDialog() == DialogResult.OK)
        {
            config = f.Result;
            ConfigManager.Save(config);
            if (!config.Enabled) paused = true;
            else if (paused) paused = false;
            trayIcon.ContextMenuStrip = BuildMenu();
        }
    }

    void StartJiggling()
    {
        if (running) return;
        running = true; paused = false;
        jiggleThread = new Thread(() => { while (running) { if (!paused) Jiggle(); Thread.Sleep(config.Interval * 1000); } }) { IsBackground = true };
        jiggleThread.Start();
    }

    void Jiggle()
    {
        var dx = (rng.Next(1, config.Pixels + 1)) * (rng.Next(2) == 0 ? -1 : 1);
        var dy = (rng.Next(1, config.Pixels + 1)) * (rng.Next(2) == 0 ? -1 : 1);
        NativeMethods.SendInput(1, [new INPUT { type = NativeMethods.INPUT_MOUSE, union = new INPUT_UNION { mi = new MOUSEINPUT { dx = dx, dy = dy, dwFlags = NativeMethods.MOUSEEVENTF_MOVE } } }], Marshal.SizeOf<INPUT>());
    }
}

class Program
{
    [STAThread]
    static void Main()
    {
        var mutex = NativeMethods.CreateMutex(IntPtr.Zero, true, "Global\\MouseJigglerSingleInstance");
        if (NativeMethods.GetLastError() == 183)
        {
            MessageBox.Show("Mouse Jiggler is already running.\nCheck your system tray.", "Mouse Jiggler", MessageBoxButtons.OK, MessageBoxIcon.Information);
            return;
        }
        Application.EnableVisualStyles();
        Application.SetCompatibleTextRenderingDefault(false);
        Application.Run(new JigglerApp());
        GC.KeepAlive(mutex);
    }
}
