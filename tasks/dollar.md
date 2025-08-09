# disallow _ at the start of any path component

# explicitly treat command names as paths, dont allow foo//bar for example

# ✅ create a type for the result of command/message parsing so that it's unit-testable

# ✅ handle $foo a b c to be $foo("a", "b", "c")

# forbid foo.name ("name" cant be set on functions)

# check what other properties cannot be set on functions

# add syntax like $foo = "bar"

let's be conservative and not allow $foo = "bar" but instead have
- $foo.text = "bar"
- $foo() { ... }
  - must work even if the command is not defined yet
  - if the command is defined, it should not create a new function but set .run
  - $foo() { } resets / removes the code

# add function definition syntax with backticks

for example,

```js
$foo() {
  return "bar"
}
```

should be the same as 

`$foo() { ... }`

also we should detect if the person tries to define multiple functions in the same block and allow it also

# when editing a message, also edit the output of the JS

# add smth like .children()

# rename .content to .text

# have args in the context

e.g. give the function stuff like 'args' when called like $foo

# ✅ `$` whitespace

any whitespace should work, e.g `$ foo`, `$\nfoo`, etc

# handle nested commands in a nicer way

just give Deno a tree, don't make it reconstruct the tree by itself

# ✅ btw move tests to be colocated with the code they test?
