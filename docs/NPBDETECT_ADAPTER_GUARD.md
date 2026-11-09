# NPBDetect predictions are not admissible

**NPBDetect predictions are not admissible evidence in the optional activity channel.** In `mamey.activity_predictions`, any model ID whose lowercase form starts with `npbdetect` must use `OUT_OF_DOMAIN` or `FAILED`. `IN_DOMAIN` and `LIMITED` produce `NONADMISSIBLE_MODEL`. Both allowed hold states require null antibacterial/antifungal probabilities and `activity_call=HOLD`; a failed or out-of-domain model is not a biological negative or numeric zero.

The audit notes below describe upstream behavior. They do not permit importing its raw probabilities into the held prediction fields. If you keep external raw output as audit evidence, store it separately with its provenance, label it non-admissible, and do not turn it into Mamey scores or measured activity.

What the sibling writer (`write_predictions`, `mamey/activity_predictions.py:278-296`) does:
- It validates the document and refuses an invalid one.
- It refuses an output folder inside the source package.
- It replaces `optional_activity_predictions.json` at the chosen destination through a fixed temporary sibling name (`<name>.tmp`).

What it does not do:
- It does not run NPBDetect.
- Its hash checks validate syntax only. They do not show that a hash matches the actual model, environment or input bytes.
- It does not keep earlier attempts or isolate concurrent writes. Choose a fresh destination to keep an earlier attempt.

Verify provenance, exact identity and source bindings yourself.

The supplied upstream commit, graph, threshold and HC/ORG observations below are preserved historical audit assertions. The local admission contract does not establish a fresh upstream download, model run or reproduction; bind those states to their own evidence.

---

## Preserved upstream adapter audit notes

### Upstream audit

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
