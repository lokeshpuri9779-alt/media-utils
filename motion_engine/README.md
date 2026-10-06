# RAYVAN Motion Engine

This folder is the installed Motion Canvas production layer for Astra.

Source project: `motion-canvas/motion-canvas`  
Packages: `@motion-canvas/core`, `@motion-canvas/2d`,
`@motion-canvas/vite-plugin`  
Pinned version: `3.17.2`  
License of the installed core/2D/plugin packages: MIT.

The GPL FFmpeg exporter is intentionally not installed. Astra keeps final
encoding in its existing FFmpeg pipeline while Motion Canvas supplies the
animation and composition layer.

CI runs `npm install` and `npm run build` so this is a real installed,
compiled dependency rather than a reference-only entry.
