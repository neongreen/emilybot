/**
 * Functions exposed to the QuickJS runtime.
 *
 * Note: any console output must be captured by the executor, so don't use console.log here.
 */
export const lib = {
  /** Random integer (inclusive) */
  random: (min: number, max: number): number => {
    return Math.floor(Math.random() * (max - min + 1)) + min
  },
}
