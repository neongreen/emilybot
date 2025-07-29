All terminal commands, at all times, must be run with `gtimeout 3s` or some other appropriate timeout.
This is extremely important.
You can't do anything while you are waiting for a command to finish and the command is waiting for a confirmation prompt (for example).
You must be able to keep working even if the user isn't around, for extended periods of time.
This means using `gtimeout` is paramount.
