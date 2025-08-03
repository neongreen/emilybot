- [ ] can we create aliases that are a persons nick. that would be neat
- [ ] enforce that aliases are essentially a path
- [ ] add output of print($) to the docs and enforce it on ci
- [ ] .add should become alias prop?
- [ ] expose Intl
- [ ] fix autoreloading
- [ ] .remind
- [ ] print($) should show docs/descriptions somehow
- [ ] semi-builtins (eg. .random could be implemented in JS, just don't let people modify/override it)
- [ ] .clone/.fork
- rename emilybot to emily (folder)
- show the bot invite link in .help

# Syntax wishlist / pain points

- `$` keeps triggering Texit

- `$.cmd("foo")` for imports is annoying, I wish for `$cmd("foo")` or `cmd.foo()` even `$foo()`
  - unclear how to handle cmds with `/` though
    - possibly I'll have `$foo()` and `$.foo()` (to see which wins)
    - `$foo.bar()` for nested commands
    - commands will get a special annotation that lets `Deno.inspect` show their contents in addition to `[Function]`
    - `.name` and whatever else is forbidden for `Function` objects is forbidden
  - our attributes become `._help`, `._content` (or `._text`), etc
  - anything starting with `_` is reserved for us
    - alternative: `cmd.Help`, `cmd.Content`, etc (big letters are reserved for us)
    - alternative: big letters are for commands, except stuff like `Date` etc
      - annoying that now people have to care about class names tho
    - alternative: `_lib.permute`, `_random`, `_randommember`, etc
      - more lightweight than `$lib.permute`, `$random`, `$randommember`?

ok proposal

> but the general idea is to have all commands become $foo objects so that we can have
>
> ```js
> $randommember.text += ",silvy"
> $randommember.text.replace(",silvy,", ",") // remove stuff
> $randommember // calls it
> $random($messages.find({ author: $randommember() })) + " -- who said it???" // quiz
> ```

> also this automatically allows having multiple emily commands in one msg
