import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import Paper from "@mui/material/Paper";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import type { OperationStep } from "../types/operation";
import {
  CELL_STATUS_COLOR,
  CELL_STATUS_LABEL,
  LOCK_STATUS_COLOR,
  LOCK_STATUS_LABEL,
  OPERATION_TYPE_LABEL,
  operationHint,
} from "../labels";

interface OperationPanelProps {
  step: OperationStep;
  busy: boolean;
  error: string | null;
  onRefreshLock: () => void;
  onActionDone: () => void;
  onConfirm: () => void;
  onCancel: () => void;
}

const BIG_BUTTON = { py: 1.75, fontSize: "1.1rem" } as const;

export function OperationPanel({
  step,
  busy,
  error,
  onRefreshLock,
  onActionDone,
  onConfirm,
  onCancel,
}: OperationPanelProps) {
  const canActionDone = step.operation_status === "WAITING_COURIER_ACTION";
  const canConfirm = step.operation_status === "READY_TO_CONFIRM";

  return (
    <Paper elevation={3} sx={{ p: { xs: 2, md: 4 }, borderRadius: 3 }}>
      <Stack spacing={3}>
        <Box>
          <Typography variant="overline" color="text.secondary">
            {OPERATION_TYPE_LABEL[step.operation_type]}
          </Typography>
          <Typography variant="h4" sx={{ fontWeight: 700 }}>
            Ячейка №{step.cell_number}
          </Typography>
        </Box>

        <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
          <Chip
            label={`Ячейка: ${CELL_STATUS_LABEL[step.cell_status]}`}
            color={CELL_STATUS_COLOR[step.cell_status]}
          />
          <Chip
            label={`Замок: ${LOCK_STATUS_LABEL[step.lock_status]}`}
            color={LOCK_STATUS_COLOR[step.lock_status]}
            variant="outlined"
          />
        </Stack>

        <Alert severity="info" icon={false} sx={{ fontSize: "1.25rem", py: 2 }}>
          {operationHint(step.operation_status, step.operation_type)}
        </Alert>

        {error !== null && <Alert severity="error">{error}</Alert>}

        <Stack spacing={2}>
          <Button
            variant="contained"
            fullWidth
            sx={BIG_BUTTON}
            disabled={busy}
            onClick={onRefreshLock}
          >
            Обновить статус замка
          </Button>

          {canActionDone && (
            <Button
              variant="contained"
              color="secondary"
              fullWidth
              sx={BIG_BUTTON}
              disabled={busy}
              onClick={onActionDone}
            >
              Я выполнил действие с товаром
            </Button>
          )}

          {canConfirm && (
            <Button
              variant="contained"
              color="success"
              fullWidth
              sx={BIG_BUTTON}
              disabled={busy}
              onClick={onConfirm}
            >
              Подтвердить операцию
            </Button>
          )}

          <Button
            variant="outlined"
            color="error"
            fullWidth
            sx={BIG_BUTTON}
            disabled={busy}
            onClick={onCancel}
          >
            Отменить операцию
          </Button>
        </Stack>
      </Stack>
    </Paper>
  );
}
