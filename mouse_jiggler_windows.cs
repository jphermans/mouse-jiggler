using System;
using System.Drawing;
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
record Config(int Interval = 60, int Pixels = 3, bool Enabled = true);

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

// ── Settings Form ────────────────────────────────────────────────────────
class SettingsForm : Form
{
    readonly TrackBar intervalBar = new() { Minimum = 5, Maximum = 600, TickFrequency = 30, Width = 300 };
    readonly TrackBar pixelsBar = new() { Minimum = 1, Maximum = 10, Width = 300 };
    readonly CheckBox enabledCheck = new() { Text = "Enable jiggling" };
    readonly Label intervalLabel = new(), pixelsLabel = new();
    readonly Button saveBtn = new() { Text = "Save" }, cancelBtn = new() { Text = "Cancel" };

    public Config Result { get; private set; }

    public SettingsForm(Config current)
    {
        Result = current;
        Text = "Mouse Jiggler — Settings";
        FormBorderStyle = FormBorderStyle.FixedDialog;
        MaximizeBox = false; MinimizeBox = false;
        StartPosition = FormStartPosition.CenterScreen;
        Size = new Size(380, 280);
        BackColor = Color.FromArgb(43, 43, 43);
        ForeColor = Color.FromArgb(224, 224, 224);

        enabledCheck.Checked = current.Enabled;
        enabledCheck.Location = new Point(20, 15);
        enabledCheck.BackColor = BackColor; enabledCheck.ForeColor = ForeColor;

        intervalBar.Value = current.Interval;
        intervalLabel.Text = $"Interval: {current.Interval}s";
        intervalLabel.Location = new Point(20, 50);
        intervalBar.Location = new Point(20, 75);
        intervalBar.Scroll += (_, _) => intervalLabel.Text = $"Interval: {intervalBar.Value}s";

        pixelsBar.Value = current.Pixels;
        pixelsLabel.Text = $"Max pixels: {current.Pixels}px";
        pixelsLabel.Location = new Point(20, 130);
        pixelsBar.Location = new Point(20, 155);
        pixelsBar.Scroll += (_, _) => pixelsLabel.Text = $"Max pixels: {pixelsBar.Value}px";

        saveBtn.Location = new Point(190, 200);
        saveBtn.Click += (_, _) => { Result = new(intervalBar.Value, pixelsBar.Value, enabledCheck.Checked); DialogResult = DialogResult.OK; Close(); };
        cancelBtn.Location = new Point(280, 200);
        cancelBtn.Click += (_, _) => { DialogResult = DialogResult.Cancel; Close(); };

        Controls.AddRange([enabledCheck, intervalLabel, intervalBar, pixelsLabel, pixelsBar, saveBtn, cancelBtn]);
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

        if (config.Enabled) StartJiggling();
    }

    static Icon MakeIcon()
    {
        var bmp = new Bitmap(32, 32);
        using var g = Graphics.FromImage(bmp);
        g.Clear(Color.Transparent);
        g.SmoothingMode = System.Drawing.Drawing2D.SmoothingMode.AntiAlias;

        // Green circle background
        using var brush = new SolidBrush(Color.FromArgb(76, 175, 80));
        g.FillEllipse(brush, 1, 1, 30, 30);

        // White mouse pointer
        using var pen = new Pen(Color.White, 2);
        var cursor = new Point[] {
            new(7,24), new(10,18), new(15,22), new(20,14), new(18,9), new(25,7),
        };
        g.DrawLines(pen, cursor);
        // Fill cursor
        using var cursorBrush = new SolidBrush(Color.White);
        var fillPts = new Point[] {
            new(7,24), new(10,18), new(15,22), new(20,14), new(18,9), new(25,7),
        };
        g.FillPolygon(cursorBrush, fillPts, System.Drawing.Drawing2D.FillMode.Winding);

        return Icon.FromHandle(bmp.GetHicon());
    }

    ContextMenuStrip BuildMenu()
    {
        var menu = new ContextMenuStrip();
        menu.Items.Add(paused ? "▶ Resume" : "⏸ Pause", null, (_, _) => { paused = !paused; trayIcon.ContextMenuStrip = BuildMenu(); });
        menu.Items.Add(new ToolStripSeparator());
        menu.Items.Add("Settings", null, (_, _) => OpenSettings());
        menu.Items.Add(new ToolStripSeparator());
        menu.Items.Add("Exit", null, (_, _) => { running = false; trayIcon.Visible = false; Application.Exit(); });
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

// ── Entry Point ──────────────────────────────────────────────────────────
class Program
{
    [STAThread]
    static void Main()
    {
        // Single instance
        var mutex = NativeMethods.CreateMutex(IntPtr.Zero, true, "Global\\MouseJigglerSingleInstance");
        if (NativeMethods.GetLastError() == 183) // ERROR_ALREADY_EXISTS
        {
            MessageBox.Show("Mouse Jiggler is already running.\nCheck your system tray.",
                "Mouse Jiggler", MessageBoxButtons.OK, MessageBoxIcon.Information);
            return;
        }

        Application.EnableVisualStyles();
        Application.SetCompatibleTextRenderingDefault(false);
        Application.Run(new JigglerApp());
    }
}
