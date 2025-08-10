import { assertEquals } from "@std/assert"
import { wrapUserCode } from "./parse.ts"

Deno.test("wrapUserCode - console.log", () => {
  assertEquals(
    wrapUserCode("console.log('hello');", "module"),
    [
      `export default (async () => {`,
      `return console.log("hello");`,
      `})()`,
    ].join("\n"),
  )
})

Deno.test("wrapUserCode - return", () => {
  assertEquals(
    wrapUserCode("return 1;", "module"),
    [
      `export default (async () => {`,
      `return 1;`,
      `})()`,
    ].join("\n"),
  )
})

Deno.test("wrapUserCode - 2+2", () => {
  assertEquals(
    wrapUserCode("2+2", "module"),
    [
      `export default (async () => {`,
      `return 2 + 2;`,
      `})()`,
    ].join("\n"),
  )
})

// Tests for import transformation functionality
Deno.test("transformImports - bare import", () => {
  const result = wrapUserCode("import 'lodash'; console.log('test');", "module")
  assertEquals(
    result,
    [
      `export default (async () => {`,
      `await import("lodash");`,
      `return console.log("test");`,
      `})()`,
    ].join("\n"),
  )
})

Deno.test("transformImports - default import", () => {
  const result = wrapUserCode("import lodash from 'lodash'; console.log(lodash);", "module")
  assertEquals(
    result,
    [
      `export default (async () => {`,
      `const lodash = (await import("lodash")).default;`,
      `return console.log(lodash);`,
      `})()`,
    ].join("\n"),
  )
})

Deno.test("transformImports - namespace import", () => {
  const result = wrapUserCode("import * as _ from 'lodash'; console.log(_.map);", "module")
  assertEquals(
    result,
    [
      `export default (async () => {`,
      `const _ = await import("lodash");`,
      `return console.log(_.map);`,
      `})()`,
    ].join("\n"),
  )
})

Deno.test("transformImports - named imports", () => {
  const result = wrapUserCode("import { map, filter } from 'lodash'; console.log(map);", "module")
  assertEquals(
    result,
    [
      `export default (async () => {`,
      `const {map, filter} = await import("lodash");`,
      `return console.log(map);`,
      `})()`,
    ].join("\n"),
  )
})

Deno.test("transformImports - named imports with aliases", () => {
  const result = wrapUserCode(
    "import { map as mapFn, filter as filterFn } from 'lodash'; console.log(mapFn);",
    "module",
  )
  assertEquals(
    result,
    [
      `export default (async () => {`,
      `const {map: mapFn, filter: filterFn} = await import("lodash");`,
      `return console.log(mapFn);`,
      `})()`,
    ].join("\n"),
  )
})

Deno.test("transformImports - mixed default and named imports", () => {
  const result = wrapUserCode("import lodash, { map, filter } from 'lodash'; console.log(lodash, map);", "module")
  assertEquals(
    result,
    [
      `export default (async () => {`,
      `const {default: lodash, map, filter} = await import("lodash");`,
      `return console.log(lodash, map);`,
      `})()`,
    ].join("\n"),
  )
})

Deno.test("transformImports - multiple import statements", () => {
  const result = wrapUserCode(
    `
    import 'lodash';
    import axios from 'axios';
    import { useState } from 'react';
    console.log('test');
  `,
    "module",
  )
  assertEquals(
    result,
    [
      `export default (async () => {`,
      `await import("lodash");`,
      `const axios = (await import("axios")).default;`,
      `const {useState} = await import("react");`,
      `return console.log("test");`,
      `})()`,
    ].join("\n"),
  )
})

Deno.test("transformImports - import with expression", () => {
  const result = wrapUserCode("import lodash from 'lodash'; 2 + 2", "module")
  assertEquals(
    result,
    [
      `export default (async () => {`,
      `const lodash = (await import("lodash")).default;`,
      `return 2 + 2;`,
      `})()`,
    ].join("\n"),
  )
})

Deno.test("transformImports - no imports, just expression", () => {
  const result = wrapUserCode("2 + 2", "module")
  assertEquals(
    result,
    [
      `export default (async () => {`,
      `return 2 + 2;`,
      `})()`,
    ].join("\n"),
  )
})

Deno.test("transformImports - import with return statement", () => {
  const result = wrapUserCode("import lodash from 'lodash'; return lodash;", "module")
  assertEquals(
    result,
    [
      `export default (async () => {`,
      `const lodash = (await import("lodash")).default;`,
      `return lodash;`,
      `})()`,
    ].join("\n"),
  )
})

Deno.test("transformImports - complex import scenario", () => {
  const result = wrapUserCode(
    `
    import React, { useState, useEffect as useEffectHook } from 'react';
    import * as utils from './utils';
    import './styles.css';
    const component = () => {};
  `,
    "module",
  )
  assertEquals(
    result,
    [
      `export default (async () => {`,
      `const {default: React, useState, useEffect: useEffectHook} = await import("react");`,
      `const utils = await import("./utils");`,
      `await import("./styles.css");`,
      `const component = () => {};`,
      `})()`,
    ].join("\n"),
  )
})
