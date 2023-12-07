package com.antmicro.update.rdfm.utilities;

public class BackoffCounter {
    private long mCurrent;
    private final long mInitialValue;
    private final long mMaxValue;

    public BackoffCounter(long initialValue, long maxValue) {
        if (initialValue > maxValue) {
            throw new IllegalArgumentException("initialValue is larger than maxValue");
        }
        mCurrent = initialValue;
        mInitialValue = initialValue;
        mMaxValue = maxValue;
    }

    /**
     * Advance the backoff counter and return the new value.
     *
     * @return new backoff value
     */
    public long next() {
        mCurrent = Math.multiplyExact(mCurrent, 2L);
        if (mCurrent > mMaxValue) {
            mCurrent = mMaxValue;
        }
        return mCurrent;
    }

    /**
     * Reset the counter to its initial value
     */
    public void reset() {
        mCurrent = mInitialValue;
    }


}
