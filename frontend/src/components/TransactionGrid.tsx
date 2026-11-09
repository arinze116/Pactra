import type { CellKeyDownEvent, ColDef, RowClickedEvent } from "ag-grid-community";
import "ag-grid-community/styles/ag-grid.css";
import "ag-grid-community/styles/ag-theme-quartz.css";
import { AgGridReact } from "ag-grid-react";
import { useMemo } from "react";
import { useNavigate } from "react-router-dom";
import type { Transaction, TransactionStatus } from "../types";
import { formatCents, Status } from "./UI";

interface TransactionGridProps {
  items: Transaction[];
}

export default function TransactionGrid({ items }: TransactionGridProps) {
  const navigate = useNavigate();
  const columns = useMemo<ColDef<Transaction>[]>(() => [
    { field: "vendor", headerName: "Vendor", flex: 1.4, minWidth: 180 },
    { field: "amount_cents", headerName: "Amount", width: 130, valueFormatter: ({ value }) => formatCents(Number(value)), cellClass: "tabular-nums" },
    { field: "category", headerName: "Category", width: 125 },
    { field: "status", headerName: "Status", width: 150, cellRenderer: ({ value }: { value: TransactionStatus }) => <Status value={value} /> },
    { field: "rail", headerName: "Rail", minWidth: 160, valueFormatter: ({ value }) => value === "internal_sandbox" ? "Internal sandbox" : "PayPal Sandbox" },
    { field: "created_at", headerName: "Created", width: 170, valueFormatter: ({ value }) => new Intl.DateTimeFormat("en-NG", { dateStyle: "medium", timeStyle: "short" }).format(new Date(String(value))) },
  ], []);

  function open(event: RowClickedEvent<Transaction>) {
    if (event.data) navigate(`/app/transactions/${event.data.id}`);
  }

  function openWithKeyboard(event: CellKeyDownEvent<Transaction>) {
    if ((event.event as KeyboardEvent | undefined)?.key === "Enter" && event.data) {
      navigate(`/app/transactions/${event.data.id}`);
    }
  }

  return <div className="ag-theme-quartz hidden h-[590px] md:block"><AgGridReact<Transaction> columnDefs={columns} rowData={items} onCellKeyDown={openWithKeyboard} onRowClicked={open} pagination paginationPageSize={25} paginationPageSizeSelector={false} rowSelection="single" /></div>;
}
