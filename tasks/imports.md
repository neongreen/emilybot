# ✅ implement `import` but only for esm.sh

# ✅ document `import`

# ✅ `import` should throw an error if any other url is used

# make `import` request the correct es version from esm.sh

# ✅ stored code should be wrapped in some way

nb. the stored code might have imports and then it can't do anything about globalThis but it seems ok.
like, either you can mess with globalThis or you can use imports.

# it should be possible to use `import` in a command

currently imports work in `$` but in commands they are transformed into `await import` and then we have to make the whole command async.
it's a mess.

what are my options?

1. when executing `$foo` directly, we will transparently use `await` on it.
   however, when calling from another command,you'd have to say `await $foo()`.
   in `$` you'd also have to say `$ await foo()`.

2. each command becomes a module rather than a function.
   `$foo` still works, but to call a command from another command, you'd have to say:

   ```js
   import $random from '$random'
   console.log($random())
   ```

   might be easier if the custom loader creates a global object, i.e.

   ```js
   import '$random'
   console.log($random())
   ```

   on the other hand this also means that you can export multiple functions from one command, which is neat.

   not sure how this interacts with sub-commands tho (which become attributes).

note that in both cases you can still call non-async commands normally.
so we could say that if you are calling an async command but haven't said `await`, it's your fault.

