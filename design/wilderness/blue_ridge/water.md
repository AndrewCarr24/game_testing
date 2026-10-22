# Laurel Fork Cove: the water (the Laurel River's look)

Status: wave 2, in progress (the river-look workstream). This file is the contract for the
water-query API first; the look notes follow once the pass is done.

## Water-query API (`viewer/wild/water.js`)

One CPU field per loaded world, shared by the renderer and the player. Coordinates are the
runtime's terrain-local three.js metres (the same as `world.heightAt(x, z)`): x east, y up,
z = -(estate y + 810).

```js
import { waterField } from './water.js';
const water = waterField(world);   // cached on the world (world.waterField): every caller gets the same one
// also window.__water once the level is built (main.js)

water.surfaceAt(x, z)          // -> water surface height y (m), NaN where dry
water.depthAt(x, z)            // -> surface - bed (m), 0 where dry (bed = world.heightAt)
water.flowAt(x, z, out?)       // -> { x, z, speed }: surface current in m/s (three.js x/z), {0,0,0} where dry;
                               //    writes into `out` if given (no allocation per call)
water.wet(x, z)                // -> true where there is water (surfaceAt is finite and depth > 0.02)
```

- Sampling is bilinear over the 1.5 m water raster (`world.water`, NaN = dry), NaN-aware at the
  banks (a dry corner takes the mean of the wet ones), so the surface is continuous where the
  water mesh is drawn.
- `flowAt` is the current the shader draws: down the water surface's slope and along the channel,
  speed from Manning's formula on the local depth and slope (pools ~0.3-0.8 m/s, riffles 1.5-2.5,
  rapids and ledges 3-5, the cascade up to 6), deflected around the boulders that stand in the
  water and slowed (and turned back, an eddy) in their lee. Use it to push a swimmer or a
  floating object.
- Beyond the square (the ribbon down the valley to the town) the API returns dry; nothing walks
  there.
- Nothing here needs three.js or the GPU: `waterField(world)` works on the loaded world alone (tests).
