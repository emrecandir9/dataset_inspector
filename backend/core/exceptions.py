"""Dataset Inspector - Custom exceptions."""


class DatasetInspectorError(Exception):
    """Base exception for Dataset Inspector."""
    pass


class ScanError(DatasetInspectorError):
    """Error during filesystem scanning."""
    pass


class DetectionError(DatasetInspectorError):
    """Error during format detection."""
    pass


class LoaderError(DatasetInspectorError):
    """Error during dataset loading."""
    pass


class AnalyzerError(DatasetInspectorError):
    """Error during analysis."""
    pass


class ReportError(DatasetInspectorError):
    """Error during report generation."""
    pass


class PathNotFoundError(DatasetInspectorError):
    """The specified path does not exist."""
    pass


class UnsupportedFormatError(DatasetInspectorError):
    """The dataset format is not supported."""
    pass
