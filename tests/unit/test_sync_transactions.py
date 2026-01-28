import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime

# Mock the quickbooks module before importing our modules
sys_modules_mock = {
    'quickbooks': Mock(),
    'quickbooks.objects': Mock(),
    'quickbooks.objects.invoice': Mock(),
    'quickbooks.objects.payment': Mock(),
}

with patch.dict('sys.modules', sys_modules_mock):
    from src.models import Invoice, Job, Customer, LineItem, Service, Payment
    from src.services.accounting.syncer_base import DependencyError
    from src.services.accounting.invoice_syncer import InvoiceSyncer
    from src.services.accounting.payment_syncer import PaymentSyncer


class TestInvoiceSyncer:
    """Test the InvoiceSyncer implementation."""
    
    @pytest.fixture
    def mock_invoice_data(self):
        """Create mock data for invoice testing."""
        customer = Mock(spec=Customer)
        customer.id = 1
        customer.quickbooks_id = "CUST_123"
        
        service = Mock(spec=Service)
        service.id = 10
        service.name = "Test Service"
        service.quickbooks_id = "SERV_456"
        
        item = Mock(spec=LineItem)
        item.description = "Line Item 1"
        item.quantity = 2.0
        item.unit_price = 50.0
        item.total_price = 100.0
        item.service = service
        
        job = Mock(spec=Job)
        job.id = 100
        job.business_id = 1
        job.customer = customer
        job.line_items = [item]
        
        invoice = Mock(spec=Invoice)
        invoice.id = 1000
        invoice.job = job
        invoice.created_at = datetime(2026, 1, 22)
        invoice.quickbooks_id = None
        
        return invoice
        
    @pytest.fixture
    def invoice_syncer(self):
        """Create an InvoiceSyncer instance for testing."""
        mock_db = AsyncMock()
        mock_qb_client = Mock()
        return InvoiceSyncer(mock_db, mock_qb_client)

    def test_map_record_complete(self, invoice_syncer, mock_invoice_data):
        """Test mapping a complete invoice record."""
        # Execute
        result = invoice_syncer._map_record(mock_invoice_data)
        
        # Verify
        assert result['CustomerRef']['value'] == "CUST_123"
        assert result['TxnDate'] == "2026-01-22"
        assert len(result['Line']) == 1
        line = result['Line'][0]
        assert line['Amount'] == 100.0
        assert line['Description'] == "Line Item 1"
        assert line['SalesItemLineDetail']['Qty'] == 2.0
        assert line['SalesItemLineDetail']['UnitPrice'] == 50.0
        assert line['SalesItemLineDetail']['ItemRef']['value'] == "SERV_456"

    def test_map_record_dependency_missing_customer(self, invoice_syncer, mock_invoice_data):
        """Test mapping fails if customer is not synced."""
        mock_invoice_data.job.customer.quickbooks_id = None
        
        # Execute & Verify
        with pytest.raises(DependencyError) as excinfo:
            invoice_syncer._map_record(mock_invoice_data)
        assert "Customer 1 is not synced" in str(excinfo.value)

    def test_map_record_dependency_missing_service(self, invoice_syncer, mock_invoice_data):
        """Test mapping fails if service is not synced."""
        mock_invoice_data.job.line_items[0].service.quickbooks_id = None
        
        # Execute & Verify
        with pytest.raises(DependencyError) as excinfo:
            invoice_syncer._map_record(mock_invoice_data)
        assert "Service 10 (Test Service) is not synced" in str(excinfo.value)

    def test_validate_record_success(self, invoice_syncer):
        """Test successful validation."""
        data = {
            'CustomerRef': {'value': 'C_1'},
            'Line': [{'Amount': 100.0}]
        }
        assert invoice_syncer._validate_record(data) is None

    def test_validate_record_no_lines(self, invoice_syncer):
        """Test validation fails if no lines."""
        data = {
            'CustomerRef': {'value': 'C_1'},
            'Line': []
        }
        assert "must have at least one line item" in invoice_syncer._validate_record(data)


class TestPaymentSyncer:
    """Test the PaymentSyncer implementation."""
    
    @pytest.fixture
    def mock_payment_data(self):
        """Create mock data for payment testing."""
        customer = Mock(spec=Customer)
        customer.id = 1
        customer.quickbooks_id = "CUST_123"
        
        job = Mock(spec=Job)
        job.customer = customer
        
        invoice = Mock(spec=Invoice)
        invoice.id = 1000
        invoice.job = job
        invoice.quickbooks_id = "INV_789"
        
        payment = Mock(spec=Payment)
        payment.id = 5000
        payment.invoice = invoice
        payment.amount = 100.0
        payment.payment_date = datetime(2026, 1, 23)
        payment.quickbooks_id = None
        
        return payment
        
    @pytest.fixture
    def payment_syncer(self):
        """Create a PaymentSyncer instance for testing."""
        mock_db = AsyncMock()
        mock_qb_client = Mock()
        return PaymentSyncer(mock_db, mock_qb_client)

    def test_map_record_complete(self, payment_syncer, mock_payment_data):
        """Test mapping a complete payment record."""
        # Execute
        result = payment_syncer._map_record(mock_payment_data)
        
        # Verify
        assert result['CustomerRef']['value'] == "CUST_123"
        assert result['TotalAmt'] == 100.0
        assert result['TxnDate'] == "2026-01-23"
        assert len(result['Line']) == 1
        line = result['Line'][0]
        assert line['Amount'] == 100.0
        assert line['LinkedTxn'][0]['TxnId'] == "INV_789"
        assert line['LinkedTxn'][0]['TxnType'] == "Invoice"

    def test_map_record_dependency_missing_invoice(self, payment_syncer, mock_payment_data):
        """Test mapping fails if invoice is not synced."""
        mock_payment_data.invoice.quickbooks_id = None
        
        # Execute & Verify
        with pytest.raises(DependencyError) as excinfo:
            payment_syncer._map_record(mock_payment_data)
        assert "Invoice 1000 is not synced" in str(excinfo.value)
