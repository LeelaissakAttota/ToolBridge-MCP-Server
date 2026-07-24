"""Tests for CSV Intelligence Engine."""

import pytest
import asyncio
import io
from datetime import datetime

from mcp_server.services.finance.csv_intelligence import (
    CSVEngine,
    ColumnType,
    AggregationFunction,
    ColumnProfile,
    CSVSchema,
    CSVFilter,
    CSVSort,
    CSVGroupBy,
    CSVStats,
    load_csv,
    csv_to_sql,
)


class TestCSVEngine:
    """Tests for CSVEngine."""

    @pytest.fixture
    def engine(self):
        """Create a fresh CSV engine."""
        return CSVEngine()

    @pytest.fixture
    def sample_csv(self):
        """Sample CSV data for testing."""
        return """symbol,price,volume,date,sector
AAPL,150.25,1000000,2024-01-15,Technology
GOOGL,2800.50,500000,2024-01-15,Technology
MSFT,380.75,750000,2024-01-15,Technology
JPM,180.50,200000,2024-01-15,Finance
BAC,45.25,300000,2024-01-15,Finance
TSLA,250.00,800000,2024-01-15,Automotive"""

    @pytest.mark.asyncio
    async def test_load_csv_string(self, engine, sample_csv):
        """Test loading CSV from StringIO."""
        schema = await engine.load_csv(io.StringIO(sample_csv))
        
        assert schema.row_count == 6
        assert schema.column_count == 5
        assert schema.has_header is True
        assert len(schema.columns) == 5
        
        # Check column types
        col_names = [c.name for c in schema.columns]
        assert "symbol" in col_names
        assert "price" in col_names
        assert "volume" in col_names
        assert "date" in col_names
        assert "sector" in col_names

    @pytest.mark.asyncio
    async def test_load_csv_bytes(self, engine, sample_csv):
        """Test loading CSV from bytes."""
        schema = await engine.load_csv(io.BytesIO(sample_csv.encode()))
        assert schema.row_count == 6

    @pytest.mark.asyncio
    async def test_filter_operations(self, engine, sample_csv):
        """Test filtering operations."""
        await engine.load_csv(io.StringIO(sample_csv))
        
        # Test equality filter
        await engine.filter([CSVFilter(column="sector", operator="eq", value="Technology")])
        
        # Test compound filter
        await engine.filter([
            CSVFilter(column="sector", operator="eq", value="Technology"),
            CSVFilter(column="price", operator="gt", value=1000)
        ])
        assert engine.row_count == 1  # Only GOOGL

    @pytest.mark.asyncio
    async def test_sort_operations(self, engine, sample_csv):
        """Test sorting operations."""
        await engine.load_csv(io.StringIO(sample_csv))
        
        # Sort by price ascending
        await engine.sort([CSVSort(column="price", ascending=True)])
        
        # Check order
        prices = []
        for row in engine.data.itertuples():
            prices.append(row.price)
        assert prices == sorted(prices)

    @pytest.mark.asyncio
    async def test_group_by_aggregation(self, engine, sample_csv):
        """Test group by and aggregation."""
        await engine.load_csv(io.StringIO(sample_csv))
        
        group_by = CSVGroupBy(
            columns=["sector"],
            aggregations={"price": [AggregationFunction.MEAN, AggregationFunction.COUNT]}
        )
        
        result = await engine.group_by(group_by)
        
        assert len(result) == 3  # Technology, Finance, Automotive
        
        # Check technology sector stats
        tech_row = result[result["sector"] == "Technology"].iloc[0]
        assert tech_row["price_mean"] > 0
        assert tech_row["price_count"] == 3

    @pytest.mark.asyncio
    async def test_select_columns(self, engine, sample_csv):
        """Test column selection."""
        await engine.load_csv(io.StringIO(sample_csv))
        await engine.select_columns(["symbol", "price"])
        
        assert list(engine.data.columns) == ["symbol", "price"]

    @pytest.mark.asyncio
    async def test_limit_offset(self, engine, sample_csv):
        """Test limit and offset."""
        await engine.load_csv(io.StringIO(sample_csv))
        await engine.limit(2, offset=1)
        
        assert len(engine.data) == 2
        assert engine.data.iloc[0]["symbol"] == "GOOGL"  # Second row (0-indexed)

    @pytest.mark.asyncio
    async def test_get_stats(self, engine, sample_csv):
        """Test statistical summary."""
        await engine.load_csv(io.StringIO(sample_csv))
        stats = await engine.get_stats()
        
        assert stats.row_count == 6
        assert stats.column_count == 5
        assert "price" in stats.numeric_columns
        assert "sector" in stats.categorical_columns
        assert "date" in stats.date_columns

    @pytest.mark.asyncio
    async def test_export_formats(self, engine, sample_csv):
        """Test exporting to various formats."""
        await engine.load_csv(io.StringIO(sample_csv))
        
        # CSV export
        csv_output = await engine.export("csv")
        assert "symbol,price,volume,date,sector" in csv_output
        
        # JSON export
        json_output = await engine.export("json")
        assert "AAPL" in json_output


class TestColumnProfiling:
    """Tests for column type detection and profiling."""

    @pytest.fixture
    def engine(self):
        return CSVEngine()

    @pytest.mark.asyncio
    async def test_integer_detection(self, engine):
        """Test integer column detection."""
        csv_data = "id,count\n1,100\n2,200\n3,300"
        schema = await engine.load_csv(io.StringIO(csv_data))
        
        id_col = next(c for c in schema.columns if c.name == "id")
        assert id_col.detected_type == ColumnType.INTEGER
        assert id_col.is_unique is True

    @pytest.mark.asyncio
    async def test_float_detection(self, engine):
        """Test float column detection."""
        csv_data = "price,ratio\n150.25,1.5\n200.50,2.0\n"
        schema = await engine.load_csv(io.StringIO(csv_data))
        
        price_col = next(c for c in schema.columns if c.name == "price")
        assert price_col.detected_type == ColumnType.FLOAT

    @pytest.mark.asyncio
    async def test_date_detection(self, engine):
        """Test date column detection."""
        csv_data = "date,value\n2024-01-15,100\n2024-01-16,200"
        schema = await engine.load_csv(io.StringIO(csv_data))
        
        date_col = next(c for c in schema.columns if c.name == "date")
        assert date_col.detected_type == ColumnType.DATE

    @pytest.mark.asyncio
    async def test_categorical_detection(self, engine):
        """Test categorical column detection."""
        csv_data = "category,value\nA,10\nA,20\nB,30\nB,40\nC,50"
        schema = await engine.load_csv(io.StringIO(csv_data))
        
        cat_col = next(c for c in schema.columns if c.name == "category")
        assert cat_col.detected_type == ColumnType.CATEGORICAL
        assert len(cat_col.top_values) == 3

    @pytest.mark.asyncio
    async def test_currency_detection(self, engine):
        """Test currency column detection."""
        csv_data = "amount\n$100.00\n$200.50\n$300.00"
        schema = await engine.load_csv(io.StringIO(csv_data))
        
        amt_col = next(c for c in schema.columns if c.name == "amount")
        assert amt_col.detected_type == ColumnType.CURRENCY


class TestConvenienceFunctions:
    """Tests for convenience functions."""

    @pytest.mark.asyncio
    async def test_load_csv(self):
        """Test load_csv convenience function."""
        csv_data = "a,b\n1,2\n3,4"
        engine = await load_csv(io.StringIO(csv_data))
        assert engine.row_count == 2

    @pytest.mark.asyncio
    async def test_csv_to_sql(self):
        """Test CSV to SQL conversion."""
        csv_data = "id,name\n1,test\n2,test2"
        engine = await load_csv(io.StringIO(csv_data))
        result = await csv_to_sql(engine, "test_table", "sqlite:///:memory:")
        
        assert "CREATE TABLE test_table" in result
        assert "INSERT INTO test_table" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])