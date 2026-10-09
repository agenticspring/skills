# Photo-first scene reference

## Asset checklist
- Confirm the image is the requested location and composition before coding.
- Confirm licensing/provenance. If user-provided or placeholder, label it in README and do not imply public commercial clearance.
- Keep the original aspect ratio and serve a web-sized optimized copy.
- Verify mobile crop separately; `cover` can hide the tree, skyline, or mountain.

## Correct layer order
```text
photo background
→ color grading / mode overlay
→ subtle mist and water shimmer
→ falling petals / rain
→ minimal controls and hero copy
```

Do not place synthetic CSS trees, block skylines, fake bridges, or gradient rivers on top of a photoreal image unless they are explicitly requested as stylized augmentation.

## Failure pattern from prior implementation
The first Tokyo attempt stacked the photograph with CSS `SakuraTree`, `Skyline`, `River`, and `Bridge` components. The result looked like a cartoon: blob flowers, generic building blocks, and artificial water. The fix was to remove those layers and keep only the photograph plus atmosphere and particles.

## Deployment diagnostic
A local Next production build can pass while the Vercel alias/custom domain still serves an old deployment or returns `404 NOT_FOUND`. Always check both URLs after push. If the alias redirects to a custom domain that 404s, redeploy the Vercel project with the correct Next preset and root directory.
