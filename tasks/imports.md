# ✅ implement `import` but only for esm.sh

# ✅ document `import`

# ✅ `import` should throw an error if any other url is used

# make `import` request the correct es version

# preload all imports found in the code so that we dont have to use async quickjs

# stored code should be wrapped in some way

nb. the stored code might have imports and then it can't do anything about globalThis but it seems ok.
like, either you can mess with globalThis or you can use imports.