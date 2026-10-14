# launchd alternative (not in use)

The weekly capture is scheduled through the Claude desktop app's scheduled
tasks (`~/.claude/scheduled-tasks/looker-yoy-weekly-capture/`), which is what
we settled on. This plist is the macOS-native alternative, kept here as a
fallback rather than deleted.

Do not load both. They would each start the capture and the second one would
die on Chrome's debugging port; the wrapper's lock now turns that collision
into a clean skip, but you would still get one useful run and one skipped run
with a confusing notification.

Trade-offs, if you ever want to switch:

- launchd runs whether or not the Claude app is open, and re-runs a slot missed
  while the Mac slept. It cannot report anything back to you beyond the log and
  a notification.
- The Claude task only runs while the app is open, but it reads the log, runs
  the consistency gate, re-captures pages that hit a quota error, and tells you
  in plain language whether the workbook can be trusted.

To use this one instead, disable the Claude task first, then:

    cp com.suntransfers.looker-yoy-weekly.plist ~/Library/LaunchAgents/
    launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.suntransfers.looker-yoy-weekly.plist

Note that `launchctl bootout` only unloads it for the current login session:
macOS reloads anything left in ~/Library/LaunchAgents at the next login, so to
disable it properly the plist has to leave that directory - which is why it
lives here.
