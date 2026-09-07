/**
 * CPython's Mersenne Twister, `getrandbits`, `_randbelow` and `random.sample`.
 *
 * Phase 0 flagged `RandomPicker` as non-portable because it draws from
 * `random.Random(seed).sample(...)`, which no JS RNG reproduces. Rather than
 * leave a hole in the strategy set, this reimplements the exact chain CPython
 * uses, so the random control baseline is bit-identical to Python:
 *
 *   Random(seed)  -> init_by_array([seed])        (_randommodule.c: random_seed)
 *   getrandbits(k)-> genrand_uint32() >> (32 - k) for k <= 32
 *   _randbelow(n) -> rejection sampling on n.bit_length() bits
 *   sample(pop, k)-> set-tracking or pool-swap, chosen by `setsize`
 *
 * Verified against Python 3.13.3 via fixtures in `test/fixtures.json`.
 *
 * Only integer seeds are supported — the only form the engine uses.
 */
const N = 624;
const M = 397;
const MATRIX_A = 0x9908b0df;
const UPPER_MASK = 0x80000000;
const LOWER_MASK = 0x7fffffff;
export class MT19937 {
  mt = new Uint32Array(N);
  mti = N + 1;
  /** `random.Random(seed)` for a non-negative integer seed. */
  constructor(seed) {
    // CPython converts abs(seed) to little-endian 32-bit words and calls
    // init_by_array. A seed below 2^32 is a single word (including 0).
    const s = Math.abs(seed);
    const key = [];
    if (s === 0) key.push(0);
    let rem = s;
    while (rem > 0) {
      key.push(rem >>> 0 === rem ? rem : rem % 0x100000000);
      rem = Math.floor(rem / 0x100000000);
    }
    this.initByArray(key.length ? key : [0]);
  }
  initGenrand(s) {
    this.mt[0] = s >>> 0;
    for (let i = 1; i < N; i++) {
      const prev = this.mt[i - 1] ^ (this.mt[i - 1] >>> 30);
      this.mt[i] = (Math.imul(1812433253, prev) + i) >>> 0;
    }
    this.mti = N;
  }
  initByArray(key) {
    this.initGenrand(19650218);
    let i = 1;
    let j = 0;
    let k = Math.max(N, key.length);
    for (; k; k--) {
      const prev = this.mt[i - 1] ^ (this.mt[i - 1] >>> 30);
      this.mt[i] =
        (((this.mt[i] ^ Math.imul(prev, 1664525)) >>> 0) + key[j] + j) >>> 0;
      i++;
      j++;
      if (i >= N) {
        this.mt[0] = this.mt[N - 1];
        i = 1;
      }
      if (j >= key.length) j = 0;
    }
    for (k = N - 1; k; k--) {
      const prev = this.mt[i - 1] ^ (this.mt[i - 1] >>> 30);
      this.mt[i] =
        (((this.mt[i] ^ Math.imul(prev, 1566083941)) >>> 0) - i) >>> 0;
      i++;
      if (i >= N) {
        this.mt[0] = this.mt[N - 1];
        i = 1;
      }
    }
    this.mt[0] = UPPER_MASK;
  }
  /** genrand_uint32 — the tempered output. */
  nextUint32() {
    if (this.mti >= N) {
      let kk = 0;
      for (; kk < N - M; kk++) {
        const y =
          ((this.mt[kk] & UPPER_MASK) | (this.mt[kk + 1] & LOWER_MASK)) >>> 0;
        this.mt[kk] =
          (this.mt[kk + M] ^ (y >>> 1) ^ (y & 1 ? MATRIX_A : 0)) >>> 0;
      }
      for (; kk < N - 1; kk++) {
        const y =
          ((this.mt[kk] & UPPER_MASK) | (this.mt[kk + 1] & LOWER_MASK)) >>> 0;
        this.mt[kk] =
          (this.mt[kk + (M - N)] ^ (y >>> 1) ^ (y & 1 ? MATRIX_A : 0)) >>> 0;
      }
      const y =
        ((this.mt[N - 1] & UPPER_MASK) | (this.mt[0] & LOWER_MASK)) >>> 0;
      this.mt[N - 1] =
        (this.mt[M - 1] ^ (y >>> 1) ^ (y & 1 ? MATRIX_A : 0)) >>> 0;
      this.mti = 0;
    }
    let y = this.mt[this.mti++];
    y = (y ^ (y >>> 11)) >>> 0;
    y = (y ^ ((y << 7) & 0x9d2c5680)) >>> 0;
    y = (y ^ ((y << 15) & 0xefc60000)) >>> 0;
    y = (y ^ (y >>> 18)) >>> 0;
    return y >>> 0;
  }
  /** `getrandbits(k)` for 0 < k <= 32 — the only range the engine needs. */
  getrandbits(k) {
    if (k <= 0 || k > 32) throw new Error(`getrandbits: unsupported k=${k}`);
    return this.nextUint32() >>> (32 - k);
  }
  /** `_randbelow(n)`: rejection sampling over n.bit_length() bits. */
  randbelow(n) {
    if (n <= 0) return 0;
    const k = 32 - Math.clz32(n); // n.bit_length()
    let r = this.getrandbits(k);
    while (r >= n) r = this.getrandbits(k);
    return r;
  }
  /**
   * `random.sample(population, k)`.
   *
   * Reproduces both branches and the `setsize` threshold that chooses between
   * them, because they consume the RNG stream differently — picking the wrong
   * branch desynchronizes every subsequent draw.
   */
  sample(population, k) {
    const n = population.length;
    if (!(k >= 0 && k <= n))
      throw new Error("Sample larger than population or is negative");
    const result = new Array(k);
    let setsize = 21;
    if (k > 5) setsize += Math.pow(4, Math.ceil(Math.log(k * 3) / Math.log(4)));
    if (n <= setsize) {
      const pool = population.slice();
      for (let i = 0; i < k; i++) {
        const j = this.randbelow(n - i);
        result[i] = pool[j];
        pool[j] = pool[n - i - 1];
      }
    } else {
      const selected = new Set();
      for (let i = 0; i < k; i++) {
        let j = this.randbelow(n);
        while (selected.has(j)) j = this.randbelow(n);
        selected.add(j);
        result[i] = population[j];
      }
    }
    return result;
  }
}
