# disallow _ at the start of any path component

# explicitly treat command names as paths, dont allow foo//bar for example

# ✅ create a type for the result of command/message parsing so that it's unit-testable

# ✅ handle $foo a b c to be $foo("a", "b", "c")

# forbid foo.name ("name" cant be set on functions)

# check what other properties cannot be set on functions

# add syntax like $foo = "bar"

btw unclear how to make it so that you can set both run() and content()

# have args in the context

e.g. give the function stuff like 'args' when called like $foo

# ✅ `$` whitespace

any whitespace should work, e.g `$ foo`, `$\nfoo`, etc

# handle nested commands in a nicer way

just give Deno a tree, don't make it reconstruct the tree by itself

# btw move tests to be colocated with the code they test?