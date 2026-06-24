import { useCallback, useEffect, useRef, useState } from "react";

/**
 * useFetch — generic GET-style data hook.
 *
 * Returns { data, loading, error, empty, refetch }. `empty` is true only
 * when the request succeeded AND the data is genuinely empty (e.g. an empty
 * array, or null/undefined) — distinct from `error`, which means the
 * request itself failed.
 */
export function useFetch(fetchFn, deps = []) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const controllerRef = useRef(null);

  const run = useCallback(() => {
    controllerRef.current?.abort();
    const controller = new AbortController();
    controllerRef.current = controller;

    setLoading(true);
    setError(null);
    fetchFn(controller.signal)
      .then((result) => {
        if (controller.signal.aborted) return;
        setData(result);
      })
      .catch((err) => {
        if (controller.signal.aborted) return;
        setError(err);
      })
      .finally(() => {
        if (controller.signal.aborted) return;
        setLoading(false);
      });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);

  useEffect(() => {
    run();
    return () => controllerRef.current?.abort();
  }, [run]);

  const isEmpty =
    !loading &&
    !error &&
    (data === null ||
      data === undefined ||
      (Array.isArray(data) && data.length === 0) ||
      (Array.isArray(data?.items) && data.items.length === 0));

  return { data, loading, error, empty: isEmpty, refetch: run };
}

/**
 * useDebouncedValue — debounces a fast-changing value (e.g. a slider) before
 * it's used to trigger a network request.
 */
export function useDebouncedValue(value, delayMs = 350) {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const t = setTimeout(() => setDebounced(value), delayMs);
    return () => clearTimeout(t);
  }, [value, delayMs]);
  return debounced;
}

/**
 * useMutation — generic POST-style hook with a manual `mutate(payload)`
 * trigger, loading/error state, and automatic in-flight request cancellation.
 */
export function useMutation(mutateFn) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const controllerRef = useRef(null);

  const mutate = useCallback(
    async (payload) => {
      controllerRef.current?.abort();
      const controller = new AbortController();
      controllerRef.current = controller;
      setLoading(true);
      setError(null);
      try {
        const result = await mutateFn(payload, controller.signal);
        if (!controller.signal.aborted) setData(result);
        return result;
      } catch (err) {
        if (!controller.signal.aborted) setError(err);
        throw err;
      } finally {
        if (!controller.signal.aborted) setLoading(false);
      }
    },
    [mutateFn]
  );

  return { data, loading, error, mutate };
}

