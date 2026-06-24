import logging
import traceback

from rest_framework import status, permissions
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework.views import APIView

from evaluation_app.permissions import IsAdminOrHR
from evaluation_app.services.sheet_importer import parse_sheet, import_from_sheet

logger = logging.getLogger(__name__)


class SheetImportView(APIView):
    """
    POST /api/import-sheet/
    POST /api/import-sheet/?dry_run=true

    Upload a CSV or XLSX file with employee data.
    """

    permission_classes = [permissions.IsAuthenticated, IsAdminOrHR]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        try:
            dry_run = request.query_params.get("dry_run", "").lower() == "true"

            rows = parse_sheet(request)
            logger.info("Sheet parsed: %d rows", len(rows))

            result = import_from_sheet(rows, dry_run=dry_run)
            logger.info("Sheet import result: %s", result.get("status"))

            if result.get("status") == "invalid":
                return Response(result, status=status.HTTP_400_BAD_REQUEST)

            return Response(
                result,
                status=status.HTTP_200_OK if dry_run else status.HTTP_201_CREATED,
            )

        except ValueError as e:
            return Response(
                {"status": "error", "detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            logger.error("SHEET IMPORT FAILED: %s: %s", type(e).__name__, e)
            logger.error(traceback.format_exc())
            return Response(
                {
                    "status": "error",
                    "error_type": type(e).__name__,
                    "detail": str(e),
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
