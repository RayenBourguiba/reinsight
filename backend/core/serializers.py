from rest_framework import serializers


class ExposureRowSerializer(serializers.Serializer):
    lob = serializers.CharField()
    peril = serializers.CharField()
    country = serializers.CharField()
    tiv = serializers.FloatField()

    region = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    premium = serializers.FloatField(required=False, allow_null=True)
    policy_id = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    location_id = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    lat = serializers.FloatField(required=False, allow_null=True)
    lon = serializers.FloatField(required=False, allow_null=True)
    inception_date = serializers.DateField(required=False, allow_null=True)
    expiry_date = serializers.DateField(required=False, allow_null=True)

    sum_insured = serializers.FloatField(required=False, allow_null=True)
    limit = serializers.FloatField(required=False, allow_null=True)
    deductible = serializers.FloatField(required=False, allow_null=True)


class BulkExposureRequestSerializer(serializers.Serializer):
    portfolio_id = serializers.IntegerField()
    rows = ExposureRowSerializer(many=True)

    # Optional knobs
    batch_size = serializers.IntegerField(required=False, default=1000, min_value=1, max_value=5000)
    max_errors = serializers.IntegerField(required=False, default=200, min_value=1, max_value=1000)

    dedup_mode = serializers.ChoiceField(
        required=False,
        choices=["none", "policy_id", "composite"],
        default="none"
    )

class AccumulationTotalsSerializer(serializers.Serializer):
    count = serializers.IntegerField()
    total_tiv = serializers.FloatField()


class AccumulationBucketSerializer(serializers.Serializer):
    key = serializers.CharField()
    count = serializers.IntegerField()
    tiv = serializers.FloatField()
    share_pct = serializers.FloatField()


class AccumulationResponseSerializer(serializers.Serializer):
    portfolio_id = serializers.IntegerField()
    group_by = serializers.CharField()
    filters = serializers.DictField(child=serializers.CharField(), required=False)
    totals = AccumulationTotalsSerializer()
    buckets = AccumulationBucketSerializer(many=True)

class TreatySerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    treaty_type = serializers.CharField()
    ceded_share_pct = serializers.FloatField(required=False, allow_null=True)
    attachment = serializers.FloatField(required=False, allow_null=True)
    limit = serializers.FloatField(required=False, allow_null=True)


class NetTotalsSerializer(serializers.Serializer):
    gross_tiv = serializers.FloatField()
    ceded_tiv = serializers.FloatField()
    net_tiv = serializers.FloatField()
    ceded_pct = serializers.FloatField()


class NetBucketSerializer(serializers.Serializer):
    key = serializers.CharField()
    count = serializers.IntegerField()
    gross_tiv = serializers.FloatField()
    ceded_tiv = serializers.FloatField()
    net_tiv = serializers.FloatField()
    ceded_pct = serializers.FloatField()


class NetResponseSerializer(serializers.Serializer):
    portfolio_id = serializers.IntegerField()
    treaty = TreatySerializer()
    count = serializers.IntegerField()
    totals = NetTotalsSerializer()
    group_by = serializers.CharField(required=False, allow_null=True)
    buckets = NetBucketSerializer(many=True)

class ScenarioTotalsSerializer(serializers.Serializer):
    count = serializers.IntegerField()
    gross_tiv = serializers.FloatField()
    ceded_tiv = serializers.FloatField()
    net_tiv = serializers.FloatField()
    ceded_pct = serializers.FloatField()


class ScenarioDeltaSerializer(serializers.Serializer):
    gross_tiv = serializers.FloatField()
    gross_tiv_pct = serializers.FloatField()
    net_tiv = serializers.FloatField()
    net_tiv_pct = serializers.FloatField()


class ScenarioBucketSerializer(serializers.Serializer):
    key = serializers.CharField()
    count = serializers.IntegerField()
    gross_tiv = serializers.FloatField()
    ceded_tiv = serializers.FloatField()
    net_tiv = serializers.FloatField()


class ScenarioBucketsSerializer(serializers.Serializer):
    baseline = ScenarioBucketSerializer(many=True)
    stressed = ScenarioBucketSerializer(many=True)


class ScenarioResponseSerializer(serializers.Serializer):
    portfolio_id = serializers.IntegerField()
    treaty = serializers.DictField(required=False, allow_null=True)
    base_filters = serializers.DictField(required=False)
    stresses = serializers.ListField(required=False)
    group_by = serializers.CharField(required=False, allow_null=True)
    baseline = ScenarioTotalsSerializer()
    stressed = ScenarioTotalsSerializer()
    delta = ScenarioDeltaSerializer()
    buckets = ScenarioBucketsSerializer(required=False, allow_null=True)


class ScenarioFiltersSerializer(serializers.Serializer):
    country = serializers.CharField(required=False, help_text="Optional country filter, e.g. FR")
    lob = serializers.CharField(required=False, help_text="Optional line of business filter, e.g. PROPERTY")
    peril = serializers.CharField(required=False, help_text="Optional peril filter, e.g. FLOOD")
    region = serializers.CharField(required=False, help_text="Optional region filter, e.g. IDF")


class ScenarioStressItemSerializer(serializers.Serializer):
    name = serializers.CharField(help_text="Human-readable name of the stress scenario.")
    tiv_factor = serializers.FloatField(help_text="Multiplier applied to TIV. Example: 1.2 means +20%.")
    filters = ScenarioFiltersSerializer(
        required=False,
        help_text="Optional filters limiting which exposures are stressed."
    )


class ScenarioRequestSerializer(serializers.Serializer):
    portfolio_id = serializers.IntegerField(help_text="Portfolio identifier.")
    treaty_id = serializers.IntegerField(
        required=False,
        allow_null=True,
        help_text="Optional treaty ID to compute gross/ceded/net stressed results."
    )
    group_by = serializers.ChoiceField(
        choices=["country", "region", "lob", "peril"],
        required=False,
        allow_null=True,
        help_text="Optional grouping dimension for bucket comparison."
    )
    base_filters = ScenarioFiltersSerializer(
        required=False,
        help_text="Optional filters applied before scenario stress."
    )
    stresses = ScenarioStressItemSerializer(
        many=True,
        help_text="List of stress assumptions to apply."
    )


class TopExposureItemSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    policy_id = serializers.CharField(required=False, allow_blank=True)
    location_id = serializers.CharField(required=False, allow_blank=True)
    lob = serializers.CharField()
    peril = serializers.CharField()
    country = serializers.CharField()
    region = serializers.CharField(required=False, allow_blank=True)
    tiv = serializers.FloatField()
    premium = serializers.FloatField(required=False, allow_null=True)


class TopExposuresFiltersSerializer(serializers.Serializer):
    country = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    lob = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    peril = serializers.CharField(required=False, allow_blank=True, allow_null=True)


class TopExposuresResponseSerializer(serializers.Serializer):
    portfolio_id = serializers.IntegerField()
    by = serializers.CharField()
    limit = serializers.IntegerField()
    filters = TopExposuresFiltersSerializer()
    count = serializers.IntegerField()
    items = TopExposureItemSerializer(many=True)

class MissingRequiredCountsSerializer(serializers.Serializer):
    lob = serializers.IntegerField()
    peril = serializers.IntegerField()
    country = serializers.IntegerField()
    tiv = serializers.IntegerField()


class MissingRequiredPctSerializer(serializers.Serializer):
    lob = serializers.FloatField()
    peril = serializers.FloatField()
    country = serializers.FloatField()
    tiv = serializers.FloatField()


class MissingRequiredSerializer(serializers.Serializer):
    counts = MissingRequiredCountsSerializer()
    pct = MissingRequiredPctSerializer()


class InvalidValuesSerializer(serializers.Serializer):
    tiv_non_positive = serializers.IntegerField()
    premium_negative = serializers.IntegerField()


class DuplicatePolicyIdSerializer(serializers.Serializer):
    policy_id = serializers.CharField()
    count = serializers.IntegerField()


class DuplicateCompositeKeySerializer(serializers.Serializer):
    policy_id = serializers.CharField()
    country = serializers.CharField()
    region = serializers.CharField(allow_blank=True)
    lob = serializers.CharField()
    peril = serializers.CharField()


class DuplicateCompositeSerializer(serializers.Serializer):
    key = DuplicateCompositeKeySerializer()
    count = serializers.IntegerField()


class DuplicatesSerializer(serializers.Serializer):
    empty_policy_id = serializers.IntegerField()
    by_policy_id_top = DuplicatePolicyIdSerializer(many=True)
    by_composite_top = DuplicateCompositeSerializer(many=True)


class OutlierExposureSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    policy_id = serializers.CharField(allow_blank=True)
    country = serializers.CharField()
    region = serializers.CharField(allow_blank=True)
    lob = serializers.CharField()
    peril = serializers.CharField()
    tiv = serializers.FloatField()


class OutliersSerializer(serializers.Serializer):
    tiv_p95 = serializers.FloatField(allow_null=True)
    tiv_p99 = serializers.FloatField(allow_null=True)
    top_tiv = OutlierExposureSerializer(many=True)


class DistributionBucketSerializer(serializers.Serializer):
    key = serializers.CharField()
    count = serializers.IntegerField()
    tiv = serializers.FloatField()


class DistributionsSerializer(serializers.Serializer):
    by_country = DistributionBucketSerializer(many=True)
    by_lob = DistributionBucketSerializer(many=True)
    by_peril = DistributionBucketSerializer(many=True)


class DataQualityTotalsSerializer(serializers.Serializer):
    exposures = serializers.IntegerField()


class DataQualityResponseSerializer(serializers.Serializer):
    portfolio_id = serializers.IntegerField()
    totals = DataQualityTotalsSerializer()
    missing_required = MissingRequiredSerializer()
    invalid_values = InvalidValuesSerializer()
    duplicates = DuplicatesSerializer()
    outliers = OutliersSerializer()
    distributions = DistributionsSerializer()
    notes = serializers.ListField(child=serializers.CharField())

class MappingSuggestionSerializer(serializers.Serializer):
    field = serializers.CharField()
    suggested_column = serializers.CharField(required=False, allow_null=True)
    confidence = serializers.FloatField()
    required = serializers.BooleanField()


class SuggestMappingResponseSerializer(serializers.Serializer):
    upload_id = serializers.CharField()
    filename = serializers.CharField()
    delimiter = serializers.CharField()
    columns = serializers.ListField(child=serializers.CharField())
    canonical_required = serializers.ListField(child=serializers.CharField())
    canonical_optional = serializers.ListField(child=serializers.CharField())
    suggestions = MappingSuggestionSerializer(many=True)
    mapping = serializers.DictField(child=serializers.CharField())
    missing_required_fields = serializers.ListField(child=serializers.CharField())
    unmapped_columns = serializers.ListField(child=serializers.CharField())
    notes = serializers.ListField(child=serializers.CharField())

class ApplyMappingOptionsSerializer(serializers.Serializer):
    max_rows = serializers.IntegerField(required=False, default=5000, min_value=1, max_value=200000)
    preview_rows = serializers.IntegerField(required=False, default=50, min_value=1, max_value=200)
    include_rows = serializers.BooleanField(required=False, default=False)


class ApplyMappingRequestSerializer(serializers.Serializer):
    mapping = serializers.DictField(
        child=serializers.CharField(),
        help_text="Canonical field -> source CSV column mapping."
    )
    options = ApplyMappingOptionsSerializer(required=False)

class ApplyMappingStatsSerializer(serializers.Serializer):
    max_rows = serializers.IntegerField()
    preview_rows = serializers.IntegerField()
    parsed_rows = serializers.IntegerField()
    valid_rows = serializers.IntegerField()
    invalid_rows = serializers.IntegerField()
    error_rows_returned = serializers.IntegerField()


class ApplyMappingRowErrorSerializer(serializers.Serializer):
    row_number = serializers.IntegerField()
    reason = serializers.CharField()
    raw_row = serializers.DictField(required=False, allow_null=True)


class ApplyMappingNextStepSerializer(serializers.Serializer):
    hint = serializers.CharField()
    endpoint = serializers.CharField()


class ApplyMappingResponseSerializer(serializers.Serializer):
    upload_id = serializers.CharField()
    filename = serializers.CharField()
    encoding = serializers.CharField()
    delimiter = serializers.CharField()
    stats = ApplyMappingStatsSerializer()
    mapping = serializers.DictField(child=serializers.CharField())
    normalized_preview = serializers.ListField(child=serializers.DictField())
    row_errors = ApplyMappingRowErrorSerializer(many=True)
    next_step = ApplyMappingNextStepSerializer()
    normalized_rows = serializers.ListField(child=serializers.DictField(), required=False)

class BulkExposureErrorSerializer(serializers.Serializer):
    index = serializers.IntegerField()
    reason = serializers.CharField()
    row = serializers.DictField(required=False)


class BulkExposureResponseSerializer(serializers.Serializer):
    portfolio_id = serializers.IntegerField()
    dedup_mode = serializers.CharField()
    received_rows = serializers.IntegerField()
    inserted_rows = serializers.IntegerField()
    skipped_duplicates = serializers.IntegerField()
    error_rows = serializers.IntegerField()
    errors = BulkExposureErrorSerializer(many=True)
    notes = serializers.ListField(child=serializers.CharField())

class ToolExecuteRequestSerializer(serializers.Serializer):
    tool = serializers.CharField(help_text="Tool name, e.g. accumulation, net_of_treaty, scenario_stress.")
    input = serializers.DictField(help_text="Tool input object.")

class UploadFileRequestSerializer(serializers.Serializer):
    file = serializers.FileField(help_text="CSV bordereau file to upload.")


class UploadFileResponseSerializer(serializers.Serializer):
    upload_id = serializers.CharField()
    status = serializers.CharField()
    filename = serializers.CharField()
    size_bytes = serializers.IntegerField()
    content_type = serializers.CharField(allow_blank=True)
    created_at = serializers.CharField()

class ExposureListItemSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    portfolio_id = serializers.IntegerField()
    lob = serializers.CharField()
    peril = serializers.CharField()
    country = serializers.CharField()
    region = serializers.CharField(required=False, allow_blank=True)
    tiv = serializers.FloatField()
    premium = serializers.FloatField(required=False, allow_null=True)
    policy_id = serializers.CharField(required=False, allow_blank=True)
    location_id = serializers.CharField(required=False, allow_blank=True)
    lat = serializers.FloatField(required=False, allow_null=True)
    lon = serializers.FloatField(required=False, allow_null=True)
    inception_date = serializers.DateField(required=False, allow_null=True)
    expiry_date = serializers.DateField(required=False, allow_null=True)
    sum_insured = serializers.FloatField(required=False, allow_null=True)
    limit = serializers.FloatField(required=False, allow_null=True)
    deductible = serializers.FloatField(required=False, allow_null=True)


class ExposureListResponseSerializer(serializers.Serializer):
    count = serializers.IntegerField()
    page = serializers.IntegerField()
    page_size = serializers.IntegerField()
    results = ExposureListItemSerializer(many=True)