from reinsight_sdk.models import UploadPreviewResponse

def test_upload_preview_response_parsing():
    payload = {
        "upload_id": "abc",
        "filename": "sample.csv",
        "encoding": "utf-8",
        "delimiter": ",",
        "columns": ["A", "B"],
        "preview_rows": [{"A": "1", "B": "2"}],
        "returned_rows": 1,
    }

    m = UploadPreviewResponse.model_validate(payload)

    assert m.upload_id == "abc"
    assert m.columns == ["A", "B"]
    assert m.preview_rows[0]["A"] == "1"