# NPBDetect optional-adapter guard

NPBDetect may be ingested only as an optional post-seal prediction channel. For the public v1.1.0
artifacts audited at commit `073886bd4a3bbe88839a7afa6a1f3bef091be193`, record warning code
`NPB_FC1_BYPASS`: the released graph's first hidden layer is not connected to its outputs.

`HC` means “report four selected output classes.” It does not mean a stricter probability threshold.
Persist all eight `ORG` probabilities and derive the `HC` view without rerunning the model.

The binary decision implemented by the released code is strict `probability > 0.5`. Preserve the raw
probability; do not translate it into a Mamey AB/AF score or measured-activity assertion.

Every row must be attributable to the exact GBK, antiSMASH version, code commit, code hash, model-weight
hash, scaler hash, environment receipt, and activity label order. A mismatch with a distributed fixture
is `HOLD — UPSTREAM_EXAMPLE_MISMATCH`, not a biological negative.

The released checkpoint cannot be converted to the described two-hidden-layer graph by a forward-method
edit because its second layer expects 1,131 inputs while the first layer emits 100. A corrected graph
requires new second-layer weights and retraining.
