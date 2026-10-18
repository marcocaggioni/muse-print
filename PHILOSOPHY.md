# Philosophy

muse-print exists for the same reason as everything in the
[muselab](https://github.com/marcocaggioni/muselab): **gadgets should remove
technical friction so the experimenter can focus on the question, not the
how.**

Printing a name tag should not require understanding USB endpoints, raster
line counting, or the Dymo printer protocol. You should be able to say
*"print a label saying Giulia"* and have a label come out — the first time,
the tenth time, always in the same place.

Three principles guided this project:

1. **The hardware knows more than the host.** The LabelWriter has a gap
   sensor that can see the label stock. The original approach ignored it and
   had the host count lines instead — a worse source of truth doing a job
   the printer could do itself. When the device can close the loop, let it.

2. **Verify with eyes, not assumptions.** A five-dollar USB microscope
   camera pointed at the printer turned a guessing game ("is the pitch
   1287 or 1400?") into an observation loop: print, look, adjust. The
   camera is what made the real fix discoverable — and provable.

3. **Document the journey, not just the answer.** The final fix is eleven
   bytes (`ESC E`) appended to a print job. The value is everything it took
   to find those eleven bytes: the driver hunt, the drift, the camera, the
   protocol reading, the overshoot gotcha. That's what this repository
   records, so the next person starts from the answer instead of the maze.

— Marco, October 2026
