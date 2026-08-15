"use client";

import { Dialog } from "@base-ui/react/dialog";
import { Button } from "@/components/ui/button";
import { STRIKE_QUALITY_TAGS, type StrikeQualityTag } from "@/lib/audit/strike-quality";

export interface StrikeQualityModalProps {
  open: boolean;
  strokesGained: number;
  onTag: (tag: StrikeQualityTag) => void;
  onSkip: () => void;
}

export function StrikeQualityModal({ open, strokesGained, onTag, onSkip }: StrikeQualityModalProps) {
  return (
    <Dialog.Root
      open={open}
      onOpenChange={(next) => {
        if (!next) onSkip();
      }}
    >
      <Dialog.Portal>
        <Dialog.Backdrop className="fixed inset-0 bg-black/40" />
        <Dialog.Popup className="fixed top-1/2 left-1/2 w-80 -translate-x-1/2 -translate-y-1/2 rounded-lg border bg-card p-4 shadow-lg">
          <Dialog.Title className="text-sm font-semibold">What happened on that shot?</Dialog.Title>
          <Dialog.Description className="mt-1 text-sm text-muted-foreground">
            This one cost you {Math.abs(strokesGained).toFixed(2)} strokes — tag the contact
            quality.
          </Dialog.Description>
          <div className="mt-3 grid grid-cols-2 gap-2">
            {STRIKE_QUALITY_TAGS.map((tag) => (
              <Button key={tag} type="button" variant="outline" onClick={() => onTag(tag)}>
                {tag}
              </Button>
            ))}
          </div>
          <Button type="button" variant="ghost" className="mt-3 w-full" onClick={onSkip}>
            Skip
          </Button>
        </Dialog.Popup>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
