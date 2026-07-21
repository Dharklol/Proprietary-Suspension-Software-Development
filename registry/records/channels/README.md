# Channel Records

Create a `CH-*` registry record only after an actual acquisition path is selected and its positive sample rate, logger device/input, clock, polarity, zero reference, and calibration ID are known.

Do not create placeholder channel records with zero or guessed sample rates. Planned sensors remain `SNS-*` records with blocked or planned `CAL-*` records until the logger binding is real. Session-specific acquisition metadata belongs in `channels.csv`; a registry channel record is appropriate only when that binding is stable across sessions and worth referencing by ID.
