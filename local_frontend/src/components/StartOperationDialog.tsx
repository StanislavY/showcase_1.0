import { useEffect, useState } from "react";
import Alert from "@mui/material/Alert";
import Button from "@mui/material/Button";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import Divider from "@mui/material/Divider";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import type { Cell } from "../types/cell";
import type { LoadStartRequest, ReplaceStartRequest } from "../types/operation";

interface StartOperationDialogProps {
  cell: Cell | null;
  busy: boolean;
  error: string | null;
  onClose: () => void;
  onStartLoad: (request: LoadStartRequest) => void;
  onStartUnload: (cellNumber: number) => void;
  onStartReplace: (request: ReplaceStartRequest) => void;
}

const BIG_BUTTON = { py: 1.5, fontSize: "1.05rem" } as const;

export function StartOperationDialog({
  cell,
  busy,
  error,
  onClose,
  onStartLoad,
  onStartUnload,
  onStartReplace,
}: StartOperationDialogProps) {
  const [productId, setProductId] = useState("");
  const [productName, setProductName] = useState("");
  const [productPrice, setProductPrice] = useState("");

  useEffect(() => {
    setProductId("");
    setProductName("");
    setProductPrice("");
  }, [cell]);

  if (cell === null) {
    return null;
  }

  const price = Number(productPrice);
  const productValid =
    productId.trim() !== "" &&
    productName.trim() !== "" &&
    productPrice.trim() !== "" &&
    Number.isFinite(price) &&
    price >= 0;

  const handleLoad = () => {
    onStartLoad({
      cell_number: cell.number,
      product_id: productId.trim(),
      product_name: productName.trim(),
      product_price: price,
    });
  };

  const handleReplace = () => {
    onStartReplace({
      cell_number: cell.number,
      new_product_id: productId.trim(),
      new_product_name: productName.trim(),
      new_product_price: price,
    });
  };

  const productFields = (
    <Stack spacing={2} sx={{ mt: 1 }}>
      <TextField
        label="Идентификатор товара"
        value={productId}
        onChange={(event) => setProductId(event.target.value)}
        fullWidth
        disabled={busy}
      />
      <TextField
        label="Название товара"
        value={productName}
        onChange={(event) => setProductName(event.target.value)}
        fullWidth
        disabled={busy}
      />
      <TextField
        label="Цена товара"
        type="number"
        value={productPrice}
        onChange={(event) => setProductPrice(event.target.value)}
        fullWidth
        disabled={busy}
        inputProps={{ min: 0, step: "0.01" }}
      />
    </Stack>
  );

  return (
    <Dialog open onClose={busy ? undefined : onClose} fullWidth maxWidth="sm">
      <DialogTitle>Ячейка №{cell.number}</DialogTitle>
      <DialogContent dividers>
        {error !== null && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {error}
          </Alert>
        )}
        {cell.status === "EMPTY" && (
          <>
            <Typography variant="subtitle1" gutterBottom>
              Загрузить товар в пустую ячейку
            </Typography>
            {productFields}
            <Button
              variant="contained"
              fullWidth
              sx={{ ...BIG_BUTTON, mt: 2 }}
              disabled={busy || !productValid}
              onClick={handleLoad}
            >
              Начать загрузку
            </Button>
          </>
        )}

        {cell.status === "LOADED" && (
          <>
            <Typography variant="subtitle1" gutterBottom>
              Товар в ячейке: {cell.product_name ?? "—"}
            </Typography>
            <Button
              variant="contained"
              color="primary"
              fullWidth
              sx={BIG_BUTTON}
              disabled={busy}
              onClick={() => onStartUnload(cell.number)}
            >
              Выгрузить товар
            </Button>

            <Divider sx={{ my: 2 }}>или замена</Divider>

            <Typography variant="subtitle2" gutterBottom>
              Заменить на новый товар
            </Typography>
            {productFields}
            <Button
              variant="outlined"
              fullWidth
              sx={{ ...BIG_BUTTON, mt: 2 }}
              disabled={busy || !productValid}
              onClick={handleReplace}
            >
              Начать замену
            </Button>
          </>
        )}

        {cell.status !== "EMPTY" && cell.status !== "LOADED" && (
          <Typography color="text.secondary">
            С этой ячейкой нельзя начать операцию в текущем состоянии.
          </Typography>
        )}
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose} disabled={busy}>
          Закрыть
        </Button>
      </DialogActions>
    </Dialog>
  );
}
