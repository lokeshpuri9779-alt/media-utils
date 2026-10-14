extends SceneTree

# Deterministic CPU-only offline benchmark. No uploads, credentials or publishing.
func _init():
    var directory = Directory.new()
    directory.make_dir_recursive("godot-benchmark-output")
    var start = OS.get_ticks_msec()
    var width = 320
    var height = 568
    var frames = 48
    var image = Image.new()
    image.create(width, height, false, Image.FORMAT_RGB8)
    for f in range(frames):
        image.lock()
        image.fill(Color(0.10, 0.17, 0.26))
        var t = float(f) / 24.0
        var x = int(160 + 65 * sin(t * 2.8))
        var y = int(340 - abs(sin(t * 5.0)) * 55)
        for py in range(max(0, y - 58), min(height, y + 58)):
            for px in range(max(0, x - 48), min(width, x + 48)):
                var dx = float(px - x) / 48.0
                var dy = float(py - y) / 58.0
                if dx * dx + dy * dy < 1.0:
                    image.set_pixel(px, py, Color(0.94, 0.58, 0.29))
        image.unlock()
        if f == 0 or f == 24 or f == 47:
            image.save_png("godot-benchmark-output/frame-%02d.png" % f)
    var elapsed = OS.get_ticks_msec() - start
    var report = {
        "engine": "godot3",
        "frames": frames,
        "fps_target": 24,
        "width": width,
        "height": height,
        "render_milliseconds": elapsed,
        "publication_allowed": false,
        "quality_approved": false,
        "benchmark_only": true
    }
    var file = File.new()
    if file.open("godot-benchmark-output/benchmark.json", File.WRITE) != OK:
        printerr("Cannot write benchmark report")
        quit(1)
        return
    file.store_string(JSON.print(report, "  "))
    file.close()
    print("ASTRA_GODOT_BENCHMARK_OK")
    quit()
