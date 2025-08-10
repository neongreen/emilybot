/**
 * Turn user code into a module that exports execution result as the default export.
 */

import { parseArgs } from "@std/cli"
import * as astring from "astring"
import { type ESTree, parse as parseAST } from "meriyah"

export type ParsedResult = {
  success: true
  ast: ESTree.Program
} | {
  success: false
  error: string
}

export function parse(code: string): ParsedResult {
  let ast
  try {
    ast = parseAST(code, {
      jsx: false,
      module: true,
      next: true,
      globalReturn: true,
    })
  } catch (error) {
    return {
      success: false,
      error: error instanceof Error ? error.message : String(error),
    }
  }

  return {
    success: true,
    ast,
  }
}

/**
 * Transform import declarations into dynamic imports that can work inside function bodies.
 * This converts static imports like `import foo from 'bar'` into dynamic imports like `const foo = (await import('bar')).default`
 */
function transformImports(ast: ESTree.Program): void {
  for (let i = 0; i < ast.body.length; i++) {
    const node = ast.body[i]
    if (node.type === "ImportDeclaration") {
      // ImportDeclaration: { type, source, specifiers, attributes }
      // We want to transform: import ... from '...'
      // Into: await import('...')
      // If there are specifiers, we want to assign them to variables.
      // e.g. import { foo } from 'bar' -> const { foo } = await import('bar')
      //      import foo from 'bar' -> const foo = (await import('bar')).default
      //      import * as foo from 'bar' -> const foo = await import('bar')
      //      import 'bar' -> await import('bar')
      const { specifiers, source } = node
      if (!specifiers || specifiers.length === 0) {
        // import 'bar'
        ast.body[i] = {
          type: "ExpressionStatement",
          expression: {
            type: "AwaitExpression",
            argument: {
              type: "ImportExpression",
              source,
            },
          },
        }
      } else {
        // There are specifiers
        // Group specifiers by type
        const defaultSpec = specifiers.find(s => s.type === "ImportDefaultSpecifier")
        const namespaceSpec = specifiers.find(s => s.type === "ImportNamespaceSpecifier")
        const namedSpecs = specifiers.filter(s => s.type === "ImportSpecifier")

        if (namespaceSpec) {
          // import * as foo from 'bar'
          ast.body[i] = {
            type: "VariableDeclaration",
            kind: "const",
            declarations: [
              {
                type: "VariableDeclarator",
                id: namespaceSpec.local,
                init: {
                  type: "AwaitExpression",
                  argument: {
                    type: "ImportExpression",
                    source,
                  },
                },
              },
            ],
          }
        } else if (defaultSpec && namedSpecs.length === 0) {
          // import foo from 'bar'
          ast.body[i] = {
            type: "VariableDeclaration",
            kind: "const",
            declarations: [
              {
                type: "VariableDeclarator",
                id: defaultSpec.local,
                init: {
                  type: "MemberExpression",
                  object: {
                    type: "AwaitExpression",
                    argument: {
                      type: "ImportExpression",
                      source,
                    },
                  },
                  property: {
                    type: "Identifier",
                    name: "default",
                  },
                  computed: false,
                  optional: false,
                },
              },
            ],
          }
        } else if (!defaultSpec && namedSpecs.length > 0) {
          // import { foo, bar as baz } from 'bar'
          ast.body[i] = {
            type: "VariableDeclaration",
            kind: "const",
            declarations: [
              {
                type: "VariableDeclarator",
                id: {
                  type: "ObjectPattern",
                  properties: namedSpecs.map(s => ({
                    type: "Property" as const,
                    key: s.imported,
                    value: s.local,
                    kind: "init" as const,
                    method: false,
                    shorthand: s.local.name === (s.imported.type === "Identifier" ? s.imported.name : s.imported.value),
                    computed: false,
                  })),
                },
                init: {
                  type: "AwaitExpression",
                  argument: {
                    type: "ImportExpression",
                    source,
                  },
                },
              },
            ],
          }
        } else if (defaultSpec && namedSpecs.length > 0) {
          // import foo, { bar as baz } from 'bar'
          // const { default: foo, bar: baz } = await import('bar')
          ast.body[i] = {
            type: "VariableDeclaration",
            kind: "const",
            declarations: [
              {
                type: "VariableDeclarator",
                id: {
                  type: "ObjectPattern",
                  properties: [
                    {
                      type: "Property",
                      key: { type: "Identifier", name: "default" },
                      value: defaultSpec.local,
                      kind: "init",
                      method: false,
                      shorthand: false,
                      computed: false,
                    },
                    ...namedSpecs.map(s => ({
                      type: "Property" as const,
                      key: s.imported,
                      value: s.local,
                      kind: "init" as const,
                      method: false,
                      shorthand:
                        s.local.name === (s.imported.type === "Identifier" ? s.imported.name : s.imported.value),
                      computed: false,
                    })),
                  ],
                },
                init: {
                  type: "AwaitExpression",
                  argument: {
                    type: "ImportExpression",
                    source,
                  },
                },
              },
            ],
          }
        }
      }
    }
  }
}

export function wrapUserCode(code: string): string {
  const parseResult = parse(code)

  if (!parseResult.success) {
    throw new Error(`Failed to parse code: ${parseResult.error}`)
  }

  // If it's an expression, we want to return the result.
  // Funny thing is that when we parse, stuff like `2+3` is still parsed as an ExpressionStatement.
  // So we go through the AST and add `return` to the last node if it's an ExpressionStatement node.

  const ast = parseResult.ast
  const lastNode = ast.body[ast.body.length - 1]

  // Directives are things like 'use strict', we don't want to returnify those.
  if (lastNode.type === "ExpressionStatement" && !lastNode.directive) {
    ast.body[ast.body.length - 1] = {
      type: "ReturnStatement",
      argument: lastNode.expression,
    }
  }

  // Transform imports to work inside function bodies
  transformImports(ast)

  return `export default (async () => {\n${astring.generate(ast)}})()`
}

// CLI functionality when module is executed directly
if (import.meta.main) {
  const args = parseArgs(Deno.args)

  if (args._.length === 0) {
    console.error("Usage: deno run parse.ts <code>")
    console.error("Example: deno run parse.ts 'console.log(\"Hello\")'")
    Deno.exit(1)
  } else if (args._.length > 1) {
    console.error("Usage: deno run parse.ts <code>")
    console.error("Multiple arguments are not supported")
    Deno.exit(1)
  }

  const code = args._[0] as string

  try {
    const result = parse(code)

    if (result.success) {
      console.log("✅ Parse successful!")
      console.log()
      console.log("AST:")
      console.log(JSON.stringify(result.ast, null, 2))
      console.log()

      console.log("Wrapped code:")
      console.log()
      console.log(wrapUserCode(code))
    } else {
      console.log("❌ Parse failed!")
      console.log("Error:", result.error)
      Deno.exit(1)
    }
  } catch (error) {
    console.error("❌ Error:", error instanceof Error ? error.message : String(error))
    Deno.exit(1)
  }
}
