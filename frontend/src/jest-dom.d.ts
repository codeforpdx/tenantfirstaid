/* eslint-disable @typescript-eslint/no-empty-object-type, @typescript-eslint/no-unused-vars, @typescript-eslint/no-explicit-any */
import type { TestingLibraryMatchers } from "@testing-library/jest-dom/matchers";

// vitest 5 gave Assertion a second type parameter (<R, T>), which no longer merges
// with the one-parameter augmentation shipped in @testing-library/jest-dom/vitest.
declare module "vitest" {
  interface Assertion<
    R extends void | Promise<void> = void,
    T = unknown,
  > extends TestingLibraryMatchers<any, T> {}
  interface AsymmetricMatchersContaining extends TestingLibraryMatchers<
    any,
    any
  > {}
}
