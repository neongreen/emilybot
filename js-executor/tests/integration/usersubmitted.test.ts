// Examples from CRC

import { assert, assertMatch } from "@std/assert"
import { assertEquals } from "@std/assert/equals"
import { omit } from "@std/collections/omit"
import { execute } from "../../executor.ts"
import type { CommandData } from "../../types.ts"

// --- Mock data ---

const makeFields = (messageText: string) => {
  const user = {
    handle: "user",
    id: "1234567890",
    name: "User",
  }

  const message = {
    text: messageText,
  }

  return {
    user,
    message,
    ctx: { user, message },
  }
}

// --- Common helpers from CRC ---

const util: CommandData = {
  name: "util",
  content: "-",
  run: `
    $user = $.ctx.user.name
    $log = console.log
    $lines = (str) => str.split("\\n")
    $words = str => str.trim().split(/\\s+/)
    $drop1 = (xs) => xs.slice(1)
    $msg = $.message.text.slice(($.message.text.search(/\\s/) + 1) || $.message.text.length)
  `,
}

Deno.test("fortune", async () => {
  const command: CommandData = {
    name: "fortune",
    content: `
      You are eating a cookie.
      You will have a good day.
    `,
    run: `
      const lines = this.content.split('\\n').map(line => line.trim()).filter(Boolean)
      const randomLine = lines[Math.floor(Math.random() * lines.length)]
      console.log(randomLine)
    `,
  }
  const result = await execute((_env) => ({}), [command], "$fortune()")
  assertEquals(omit(result, ["output"]), { success: true, value: undefined })
  assert(["You are eating a cookie.", "You will have a good day."].includes(result.output))
})

Deno.test("good girl", async () => {
  const good: CommandData = {
    name: "good",
    content: "",
    run: `
      $util()
      if ($msg === "girl") $log('thanks ❤️')
      else if ($msg === "boy") $log('⚰️')
      else if ($msg === "bot") $log('i prefer good girl but thanks')
      else $log('alr ig')
    `,
  }
  const result = await execute((_env) => makeFields("$good girl"), [util, good], "$good('girl')")
  assertEquals(omit(result, ["output"]), { success: true, value: undefined })
  assertEquals(result.output, "thanks ❤️")
})

Deno.test("randint", async () => {
  const command: CommandData = {
    name: "randint",
    content: "random numer",
    run:
      "let rawMessage = $.message.text;\n\n// Remove command prefix if present\nif (typeof rawMessage === 'string' && rawMessage.startsWith('.randint')) {\n    rawMessage = rawMessage.slice(9).trim(); // remove '.randint'\n}\n\nlet words = rawMessage.split(' ');\nlet x = parseInt(words[0], 10);\nlet y = words.length > 1 ? parseInt(words[1], 10) : 1;\nlet lower = Math.min(x,y)\nlet upper = Math.max(x,y)\n\nif (Number.isInteger(upper) && Number.isInteger(lower) && lower <= upper) {\n    let result = Math.floor(Math.random() * (upper - lower + 1)) + lower;\n    console.log(`## You rolled between ${lower} and ${upper} and got *${result}*`);\n} else {\n    console.log(`## Command guide:\n- \\`.randint 20\\` -> <:good:1363720964810080316> Rolls between 1 and 20\n- \\`.randint 10 20\\` -> <:good:1363720964810080316> Rolls between 10 and 20\n- \\`.randint 20 10\\` -> <:good:1363720964810080316> Rolls between 10 and 20\n\\`.randint x y\\` = **Chooses a random number between x and y or between y and x.**\n** **`);\n}\n\nvar timestamp = '<t:' + Math.floor(Date.now() / 1000) + ':t>';\nconsole.log(`-# <@${$.user.id}> used .randint at ${timestamp}`);",
  }
  const result = await execute((_env) => makeFields(".randint 1 10"), [util, command], "$randint()")
  assertEquals(omit(result, ["output"]), { success: true, value: undefined })

  // Check that the output contains the expected pattern for a random number between 1 and 10
  const firstLine = result.output.split("\n")[0]
  const patternMatch = firstLine.match(/^## You rolled between 1 and 10 and got \*\d+\*$/)
  assert(patternMatch !== null, `First line does not match expected pattern: ${firstLine}`)

  // Verify the random number is within the expected range (1-10)
  const match = firstLine.match(/\*(\d+)\*/)
  assert(match !== null, `Could not extract number from first line: ${firstLine}`)
  const number = parseInt(match[1], 10)
  assert(number >= 1 && number <= 10, `Number ${number} is not in expected range [1, 10]`)

  // Also verify the output contains the timestamp line
  assert(result.output.includes("-# <@1234567890> used .randint at <t:"), "Missing timestamp line")
})

Deno.test("pingall", async () => {
  const command: CommandData = {
    name: "pingall",
    content: "",
    run: "console.log(\"@\" + \"everyone\")",
  }
  const result = await execute((_env) => ({}), [command], "$pingall()")
  assertEquals(result, { success: true, value: undefined, output: "@everyone" })
})

Deno.test("sha256", async () => {
  const sha256Command: CommandData = {
    name: "sha256",
    content: "",
    run:
      "function sha256(r){function o(r,o){return r>>>o|r<<32-o}for(var f,a,t=Math.pow,h=t(2,32),n=\"length\",c=\"\",e=[],i=8*r[n],s=sha256.h=sha256.h||[],u=sha256.k=sha256.k||[],v=u[n],l={},p=2;v<64;p++)if(!l[p]){for(f=0;f<313;f+=p)l[f]=p;s[v]=t(p,.5)*h|0,u[v++]=t(p,1/3)*h|0}for(r+=\"\";r[n]%64-56;)r+=\"\\0\";for(f=0;f<r[n];f++){if((a=r.charCodeAt(f))>>8)return;e[f>>2]|=a<<(3-f)%4*8}for(e[e[n]]=i/h|0,e[e[n]]=i,a=0;a<e[n];){var g=e.slice(a,a+=16),k=s.slice(0);for(f=0;f<64;f++){var d=g[f-15],w=g[f-2],A=s[0],C=s[4],M=s[7]+(o(C,6)^o(C,11)^o(C,25))+(C&s[5]^~C&s[6])+u[f]+(g[f]=f<16?g[f]:g[f-16]+(o(d,7)^o(d,18)^d>>>3)+g[f-7]+(o(w,17)^o(w,19)^w>>>10)|0);(s=[M+((o(A,2)^o(A,13)^o(A,22))+(A&s[1]^A&s[2]^s[1]&s[2]))|0].concat(s))[4]=s[4]+M|0,s.pop()}for(f=0;f<8;f++)s[f]=s[f]+k[f]|0}for(f=0;f<8;f++)for(a=3;a+1;a--){var S=s[f]>>8*a&255;c+=(S<16?\"0\":\"\")+S.toString(16)}return c}\n\nstart = Date.now()\njoinedargs = args.join(\" \")\nhash = sha256(joinedargs)\nend = Date.now()\n\nconsole.log(`SHA-256 hash for ${joinedargs} is ${hash}`)\nconsole.log(`Time processed: ${end-start} ms`)",
  }
  const args = ["hello", "world"]
  const result = await execute((_env) => ({ args }), [sha256Command], `$sha256(...args)`)
  const expectedHash = "b94d27b9934d3e08a52e52d7da7dabfac484efe37a5380ee9088f7ace2efcde9"
  const lines = result.output.split("\n")
  assertEquals(lines[0], `SHA-256 hash for hello world is ${expectedHash}`)
  assertMatch(lines[1], /Time processed: \d+ ms/)
  assertEquals(omit(result, ["output"]), { success: true, value: undefined })
})
