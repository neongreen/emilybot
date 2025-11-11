# Nixpacks UV Version Configuration - Comprehensive Research

## Current Project State

### Files with UV Version Specifications:
1. **`.tool-versions`**: `uv 0.7.18`
2. **`nixpacks.toml`**: `NIXPACKS_UV_VERSION = "0.8.17"`
3. **`mise.toml`**: `uv = "latest"` (not used by nixpacks)

### Latest Available Versions:
- **UV latest version**: `0.9.8` (as of Nov 7, 2025)
- **Nixpacks default**: `0.4.30` (hardcoded constant)

---

## Configuration Priority Order

Nixpacks uses the following priority order (lowest to highest):

1. **Provider** (lowest) - Auto-detected configuration, including `.tool-versions`
2. **File** - `nixpacks.toml` configuration
3. **Environment** - Environment variables passed to the build
4. **CLI** - Command-line flags (highest)

**Important**: A non-null value at a higher priority level will override lower priority values.

---

## All Ways to Set UV Version in Nixpacks

### Method 1: `.tool-versions` File (Provider Level - Lowest Priority)
**File**: `.tool-versions`
```
uv 0.7.18
```

**How it works**:
- Nixpacks Python provider reads this file using `parse_tool_versions_uv_version()`
- Automatically sets `NIXPACKS_UV_VERSION` environment variable
- This is the **lowest priority** method

**Current status**: ✅ Exists (version 0.7.18)

---

### Method 2: `nixpacks.toml` Variables (File Level)
**File**: `nixpacks.toml`
```toml
[variables]
NIXPACKS_UV_VERSION = "0.8.17"
```

**How it works**:
- Variables in this section become environment variables in the final image
- **Should override** `.tool-versions` values
- This is the recommended approach for deployment platforms like Coolify

**Current status**: ✅ Exists (version 0.8.17)
**Expected behavior**: Should override `.tool-versions` value

---

### Method 3: Environment Variables (Environment Level)
**Platform**: Coolify, Railway, or deployment platform UI

Set environment variable:
```bash
NIXPACKS_UV_VERSION=0.9.8
```

**How it works**:
- Set as a build-time environment variable in your deployment platform
- **Overrides both** `.tool-versions` and `nixpacks.toml` variables
- Highest priority besides CLI flags

**Current status**: ❌ Not currently set
**Priority**: Higher than both `.tool-versions` and `nixpacks.toml`

---

### Method 4: Direct nixpacks.toml Install Phase Override
**File**: `nixpacks.toml`
```toml
[phases.setup]
cmds = [
  "pip install uv==0.9.8"
]
```

**How it works**:
- Directly installs a specific UV version during setup phase
- Bypasses the provider's automatic UV installation
- Most explicit control over UV version

**Current status**: ❌ Not currently used

---

### Method 5: Use Nix Package (Alternative Approach)
**File**: `nixpacks.toml`
```toml
[phases.setup]
nixPkgs = [
  "...",
  "uv"  # Uses nixpkgs version
]
```

**How it works**:
- Installs UV from nixpkgs instead of via pip
- Version depends on the nixpkgs archive version
- Can specify archive for specific UV version:

```toml
[phases.setup]
nixpkgsArchive = "<specific-commit-hash>"
nixPkgs = ["...", "uv"]
```

**Current status**: ❌ Not currently used

---

## How Nixpacks Installs UV

From the source code analysis (`src/providers/python.rs`):

```rust
const UV_VERSION: &str = "0.4.30";  // Default fallback
```

Installation command used:
```bash
pip install uv==$NIXPACKS_UV_VERSION
```

**Key insight**: As of UV 0.4.30, the UV version is **not** specified in `uv.lock` or `pyproject.toml`, which is why explicit configuration is necessary.

---

## Troubleshooting Guide

### Issue: Configuration Not Working

**Potential causes**:

1. **Coolify-specific issue**: Environment variables in `nixpacks.toml` [variables] may not be properly passed in some Coolify versions
   - **Solution**: Set `NIXPACKS_UV_VERSION` as a build environment variable in Coolify UI

2. **Cache issue**: Previous builds may be cached
   - **Solution**: Set `NIXPACKS_NO_CACHE=1` to disable caching

3. **Version string format**: Some platforms are sensitive to version format
   - **Try**: Both `0.8.17` and `==0.8.17` formats

4. **Platform differences**: Coolify vs Railway vs Railway's Railpack handle nixpacks differently
   - **Note**: Railway is moving away from nixpacks to Railpack

### Recommended Testing Order:

1. **First**: Update `.tool-versions` to match latest version
   ```
   uv 0.9.8
   ```

2. **Second**: Update `nixpacks.toml` [variables]
   ```toml
   [variables]
   NIXPACKS_UV_VERSION = "0.9.8"
   ```

3. **Third**: Set environment variable in Coolify UI
   ```
   NIXPACKS_UV_VERSION=0.9.8
   ```

4. **Fourth**: Direct installation override in nixpacks.toml
   ```toml
   [phases.setup]
   cmds = [
     "...",
     "pip install uv==0.9.8"
   ]
   ```

5. **Last resort**: Use nixpkgs instead of pip
   ```toml
   [phases.setup]
   nixPkgs = ["...", "uv"]
   ```

---

## Related Environment Variables

Other nixpacks environment variables that may be relevant:

- `NIXPACKS_PYTHON_VERSION` - Python version
- `NIXPACKS_PYTHON_PACKAGE_MANAGER` - Force use of specific package manager (`uv`, `pip`, `poetry`, `pdm`, `pipenv`, `auto`)
- `NIXPACKS_NO_CACHE` - Disable build caching
- `NIXPACKS_INSTALL_CMD` - Override install command
- `NIXPACKS_BUILD_CMD` - Override build command
- `NIXPACKS_START_CMD` - Override start command

---

## Recommended Next Steps

### Option A: Update All Version Specifications
Update all files to use the latest UV version (0.9.8):

1. Update `.tool-versions`:
   ```
   uv 0.9.8
   ```

2. Update `nixpacks.toml`:
   ```toml
   [variables]
   NIXPACKS_UV_VERSION = "0.9.8"
   ```

### Option B: Remove Conflicting Configurations
Since `nixpacks.toml` [variables] should override `.tool-versions`, try removing the `.tool-versions` UV entry:

1. Keep only in `nixpacks.toml`:
   ```toml
   [variables]
   NIXPACKS_UV_VERSION = "0.9.8"
   ```

2. Remove `uv 0.7.18` from `.tool-versions` (or comment it out)

### Option C: Use Coolify Environment Variable
Set `NIXPACKS_UV_VERSION` directly in Coolify's environment variables UI (highest priority except CLI):

```
NIXPACKS_UV_VERSION=0.9.8
```

### Option D: Explicit Installation
Most explicit control - install UV directly in nixpacks.toml:

```toml
[phases.setup]
nixPkgs = [
  "...",
  "sops",
  "age",
  "unzip",
]
cmds = [
  # Install specific UV version explicitly
  "pip install uv==0.9.8",
  # Download Deno
  "curl -fsSL https://deno.land/install.sh | sh -s v2.4.1",
]
```

---

## References

- [Nixpacks Python Provider Docs](https://nixpacks.com/docs/providers/python)
- [Nixpacks Configuration File Reference](https://nixpacks.com/docs/configuration/file)
- [Nixpacks Environment Variables](https://nixpacks.com/docs/configuration/environment)
- [Nixpacks Python Provider Source Code](https://github.com/railwayapp/nixpacks/blob/main/src/providers/python.rs)
- [UV Releases](https://github.com/astral-sh/uv/releases)
- [Coolify Nixpacks Documentation](https://coolify.io/docs/builds/packs/nixpacks)
