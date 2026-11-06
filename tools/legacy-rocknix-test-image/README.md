# Legacy: custom ROCKNIX test image (superseded)

These scripts built a self-assembled ROCKNIX image with a rebuilt kernel
(Linux 7.1.2) for UAC2. That image never booted on the RG40XX H: ROCKNIX
uses Linux **7.2** for H700, and the bootloader/DTB were swapped by hand.

They are kept only for reference. The working setup is the **official**
ROCKNIX 20261101 DDR4 image plus two out-of-tree modules — see
[`rocknix/`](../../rocknix/) and the main README.
