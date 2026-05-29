package main

/*
#cgo LDFLAGS: -lX11
#include <X11/Xlib.h>
#include <stdlib.h>
*/
import "C"

import (
	"encoding/json"
	"fmt"
	"math/rand"
	"os"
	"path/filepath"
	"time"
	"unsafe"

	"github.com/getlantern/systray"
)

// ── Config ────────────────────────────────────────────────────────────────
type Config struct {
	Interval int  `json:"interval"`
	Pixels   int  `json:"pixels"`
	Enabled  bool `json:"enabled"`
}

func configDir() string {
	dir := os.Getenv("XDG_CONFIG_HOME")
	if dir == "" {
		home, _ := os.UserHomeDir()
		dir = filepath.Join(home, ".config")
	}
	return filepath.Join(dir, "mouse-jiggler")
}

func configPath() string { return filepath.Join(configDir(), "config.json") }

func loadConfig() Config {
	cfg := Config{Interval: 60, Pixels: 3, Enabled: true}
	data, err := os.ReadFile(configPath())
	if err != nil {
		return cfg
	}
	json.Unmarshal(data, &cfg)
	return cfg
}

func saveConfig(cfg Config) {
	os.MkdirAll(configDir(), 0755)
	data, _ := json.MarshalIndent(cfg, "", "  ")
	os.WriteFile(configPath(), data, 0644)
}

// ── Mouse Movement (Xlib via cgo) ────────────────────────────────────────
func jiggleMouse(pixels int) {
	dx := (rand.Intn(pixels) + 1)
	if rand.Intn(2) == 0 {
		dx = -dx
	}
	dy := (rand.Intn(pixels) + 1)
	if rand.Intn(2) == 0 {
		dy = -dy
	}

	display := C.XOpenDisplay(nil)
	if display == nil {
		return
	}
	defer C.XCloseDisplay(display)

	root := C.XDefaultRootWindow(display)

	var rx, ry, wx, wy C.int
	var mask C.uint
	var rootRet, childRet C.Window

	C.XQueryPointer(display, root, &rootRet, &childRet, &rx, &ry, &wx, &wy, &mask)

	C.XWarpPointer(display, 0, root, 0, 0, 0, 0, rx+C.int(dx), ry+C.int(dy))
	C.XFlush(display)
}

// ── Tray App ─────────────────────────────────────────────────────────────
func main() {
	systray.Run(onReady, onExit)
}

func onReady() {
	cfg := loadConfig()

	// Set up tray icon (18x18 green circle)
	systray.SetIcon(makeIcon())
	systray.SetTitle("Mouse Jiggler")
	systray.SetTooltip("Mouse Jiggler")

	// Menu
	mPause := systray.AddMenuItem("⏸ Pause", "Pause/Resume jiggling")
	mInterval := systray.AddMenuItem("Interval", "")
	mPixels := systray.AddMenuItem("Pixels", "")
	systray.AddSeparator()
	mConfig := systray.AddMenuItem("Open Config File", "Edit config.json")
	mAbout := systray.AddMenuItem("About Mouse Jiggler", "")
	systray.AddSeparator()
	mQuit := systray.AddMenuItem("Quit", "Exit")

	// Interval submenu
	intervals := []struct {
		secs int
		name string
	}{
		{30, "30s"}, {60, "60s"}, {120, "2min"}, {300, "5min"}, {600, "10min"},
	}
	for _, iv := range intervals {
		item := mInterval.AddSubMenuItem(iv.name, "")
		secs := iv.secs
		if iv.secs == cfg.Interval {
			item.Check()
		}
		go func() {
			for range item.ClickedCh {
				cfg.Interval = secs
				saveConfig(cfg)
				refreshChecks(mInterval, intervals, func(s struct {
					secs int
					name string
				}) bool { return s.secs == cfg.Interval })
			}
		}()
	}

	// Pixels submenu
	pxValues := []int{1, 2, 3, 5, 10}
	for _, px := range pxValues {
		label := fmt.Sprintf("%dpx", px)
		item := mPixels.AddSubMenuItem(label, "")
		val := px
		if px == cfg.Pixels {
			item.Check()
		}
		go func() {
			for range item.ClickedCh {
				cfg.Pixels = val
				saveConfig(cfg)
				// Refresh
			}
		}()
	}

	// Jiggle loop
	paused := false
	stop := make(chan struct{})
	if cfg.Enabled {
		go func() {
			for {
				select {
				case <-stop:
					return
				default:
					if !paused {
						jiggleMouse(cfg.Pixels)
					}
					time.Sleep(time.Duration(cfg.Interval) * time.Second)
				}
			}
		}()
	}

	// Pause toggle
	go func() {
		for range mPause.ClickedCh {
			paused = !paused
			if paused {
				mPause.SetTitle("▶ Resume")
			} else {
				mPause.SetTitle("⏸ Pause")
			}
		}
	}()

	// Open config
	go func() {
		for range mConfig.ClickedCh {
			saveConfig(cfg)
			// Try opening with xdg-open
			path := configPath()
			os.StartProcess("/usr/bin/xdg-open", []string{"xdg-open", path}, &os.ProcAttr{})
		}
	}()

	// About
	go func() {
		for range mAbout.ClickedCh {
			// Just log to stderr — no native dialog in pure Go
			fmt.Fprintf(os.Stderr, "Mouse Jiggler v1.0.0\nKeeps your screen awake with imperceptible mouse movement.\nCreated by Jean-Pierre Hermans\nhttps://github.com/jphermans/mouse-jiggler\n")
		}
	}()

	// Quit
	go func() {
		<-mQuit.ClickedCh
		close(stop)
		systray.Quit()
	}()
}

func onExit() {}

func refreshChecks(parent *systray.MenuItem, intervals []struct {
	secs int
	name string
}, match func(struct {
	secs int
	name string
}) bool) {
	// Menu items don't have easy per-item reference in systray, skip for now
}

func makeIcon() []byte {
	// 22x22 green circle with white mouse pointer — raw RGBA
	size := 22
	img := make([]byte, size*size*4)

	// Helper to check if point is inside mouse pointer polygon
	inPointer := func(x, y int) bool {
		// Mouse pointer shape: (5,16)->(7,12)->(11,15)->(14,9)->(12,6)->(17,4)
		pts := [][2]int{{5, 16}, {7, 12}, {11, 15}, {14, 9}, {12, 6}, {17, 4}}
		// Simple point-in-polygon via winding
		inside := false
		j := len(pts) - 1
		for i := 0; i < len(pts); i++ {
			if (pts[i][1] > y) != (pts[j][1] > y) &&
				x < (pts[j][0]-pts[i][0])*(y-pts[i][1])/(pts[j][1]-pts[i][1])+pts[i][0] {
				inside = !inside
			}
			j = i
		}
		return inside
	}

	for y := 0; y < size; y++ {
		for x := 0; x < size; x++ {
			dx := float64(x) - 11
			dy := float64(y) - 11
			idx := (y*size + x) * 4

			if dx*dx+dy*dy <= 100 { // circle radius 10
				if inPointer(x, y) {
					// White pointer
					img[idx] = 255
					img[idx+1] = 255
					img[idx+2] = 255
					img[idx+3] = 255
				} else {
					// Green circle
					img[idx] = 76
					img[idx+1] = 175
					img[idx+2] = 80
					img[idx+3] = 255
				}
			}
		}
	}
	return img
}

// Keep the import used
var _ = unsafe.Sizeof(0)
