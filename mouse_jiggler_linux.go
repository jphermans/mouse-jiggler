package main

/*
#cgo LDFLAGS: -lX11
#include <X11/Xlib.h>
*/
import "C"

import (
	"encoding/json"
	"fmt"
	"math/rand"
	"os"
	"os/signal"
	"path/filepath"
	"syscall"
	"time"
)

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

func jiggleMouse(pixels int) {
	dx := (rand.Intn(pixels) + 1)
	if rand.Intn(2) == 0 { dx = -dx }
	dy := (rand.Intn(pixels) + 1)
	if rand.Intn(2) == 0 { dy = -dy }

	display := C.XOpenDisplay(nil)
	if display == nil { return }
	defer C.XCloseDisplay(display)

	root := C.XDefaultRootWindow(display)
	var rx, ry, wx, wy C.int
	var mask C.uint
	var rootRet, childRet C.Window
	C.XQueryPointer(display, root, &rootRet, &childRet, &rx, &ry, &wx, &wy, &mask)
	C.XWarpPointer(display, 0, root, 0, 0, 0, 0, rx+C.int(dx), ry+C.int(dy))
	C.XFlush(display)
}

func main() {
	cfg := loadConfig()
	fmt.Printf("Mouse Jiggler — running (interval=%ds, pixels=%dpx)\n", cfg.Interval, cfg.Pixels)
	fmt.Printf("Config: %s\n", configPath())
	fmt.Println("Press Ctrl+C to stop.")

	sig := make(chan os.Signal, 1)
	signal.Notify(sig, syscall.SIGINT, syscall.SIGTERM)

	stop := make(chan struct{})
	go func() {
		for {
			select {
			case <-stop: return
			default:
				// Reload config each tick so file edits take effect
				cfg = loadConfig()
				if cfg.Enabled {
					jiggleMouse(cfg.Pixels)
				}
				time.Sleep(time.Duration(cfg.Interval) * time.Second)
			}
		}
	}()

	<-sig
	close(stop)
	fmt.Println("\nStopped.")
}
