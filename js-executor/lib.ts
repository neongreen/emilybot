/**
 * Functions exposed to the QuickJS runtime.
 *
 * TODO: how exactly does prototype pollution work and is it a risk?
 */
export const lib = (env: { consoleLog: (...args: any[]) => void }) => ({
  // Math
  min: Math.min,
  max: Math.max,

  // Arrays
  // count, // TODO: idk if it's safe to expose a function that executes whatever predicate comes from QuickJS
  tail,
  init,
  drop,
  dropLast,
  reverse,

  // Randomness
  random,
  shuffle,

  // IO
  print: (...args: any[]) => {
    env.consoleLog(...args)
  },
})

/** Count the number of elements in an array that satisfy a predicate */
// function count<T>(array: T[], predicate: (x: T) => boolean): number {
//   return array.filter(predicate).length
// }

/** Remove the first element */
function tail<T>(array: T[]): T[] {
  return array.slice(1)
}

/** Remove the first N elements */
function drop<T>(array: T[], n: number): T[] {
  return array.slice(n)
}

/** Remove the last element */
function init<T>(array: T[]): T[] {
  return array.slice(0, -1)
}

/** Remove the last N elements */
function dropLast<T>(array: T[], n: number): T[] {
  return array.slice(0, -n)
}

/** Reverse an array */
function reverse<T>(array: T[]): T[] {
  return [...array].reverse()
}

/** Random integer (inclusive) or random element from an array */
function random<T>(arr: T[]): T
function random(min: number, max: number): number
function random(...args: any[]): any {
  if (args.length === 1) {
    const arg = args[0]
    // check if it's an array
    if (Array.isArray(arg)) {
      return arg[Math.floor(Math.random() * arg.length)]
    } else {
      throw new Error(
        `random(x) expects x to be an array, got ${typeof arg}. If you want to generate a random number, use random(min, max).`,
      )
    }
  } else if (args.length === 2) {
    return Math.floor(Math.random() * (args[1] - args[0] + 1)) + args[0]
  } else {
    throw new Error(
      `random can be used either like random([x, y, ...]) (with one argument) or random(min, max) (with two arguments), got ${args.length} arguments.`,
    )
  }
}

/** Shuffle an array */
function shuffle<T>(array: T[]): T[] {
  const result = [...array]
  for (let i = array.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1))
    ;[result[i], result[j]] = [result[j], result[i]]
  }
  return result
}
