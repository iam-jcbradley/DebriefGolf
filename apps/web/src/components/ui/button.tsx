import { Button as ButtonPrimitive } from "@base-ui/react/button"
import { cva, type VariantProps } from "class-variance-authority"

import { cn } from "@/lib/utils"

const buttonVariants = cva(
  // Focus is a crisp outline (STYLE_GUIDE.md §4, Focus), not the shadcn
  // default `ring` — a soft blurred halo is exactly the kind of glow the
  // guide's "avoid shadows" rule already rejects for surfaces, and on the
  // `destructive` variant the ring rendered as a pale pink halo unlike
  // anything else in the palette.
  // `outline-none` (unconditional) sets outline-style:none, and `outline-2`
  // alone only sets width — without something to put outline-style back to
  // solid, the outline stays invisible at every width. The bare `outline`
  // utility would do that, but tailwind-merge treats `outline` and
  // `outline-2` as the same conflict group and silently drops whichever
  // comes first, no matter the order — `outline-solid` is a distinct group
  // to twMerge, so it survives alongside `outline-2`. Confirmed by reading
  // the actual computed style, not just the class list: the bare-`outline`
  // version passed a visual check of the source but rendered outline-style
  // "none" in the browser the whole time.
  "group/button inline-flex shrink-0 items-center justify-center rounded-lg border border-transparent bg-clip-padding text-sm font-medium whitespace-nowrap transition-colors outline-none select-none focus-visible:outline-solid focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring active:not-aria-[haspopup]:translate-y-px disabled:pointer-events-none disabled:opacity-50 aria-invalid:border-destructive aria-invalid:outline-solid aria-invalid:outline-destructive [&_svg]:pointer-events-none [&_svg]:shrink-0 [&_svg:not([class*='size-'])]:size-4",
  {
    variants: {
      variant: {
        default: "bg-primary text-primary-foreground hover:bg-accent-hover",
        outline:
          "border-border bg-background hover:bg-muted hover:text-foreground aria-expanded:bg-muted aria-expanded:text-foreground dark:border-input dark:bg-input/30 dark:hover:bg-input/50",
        secondary:
          "bg-secondary text-secondary-foreground hover:bg-[color-mix(in_oklch,var(--secondary),var(--foreground)_5%)] aria-expanded:bg-secondary aria-expanded:text-secondary-foreground",
        ghost:
          "text-foreground hover:bg-muted hover:text-foreground aria-expanded:bg-muted aria-expanded:text-foreground dark:hover:bg-muted/50",
        // Hairline outline, not a filled tint — a 10% rust fill rendered as
        // pale pink, the one control in the app that didn't read as ink,
        // paper, or the fairway accent (STYLE_GUIDE.md §4, "structure from
        // hairlines").
        destructive:
          "border-destructive/40 bg-transparent text-destructive hover:bg-destructive/8 dark:hover:bg-destructive/15",
        link: "text-primary underline-offset-4 hover:underline",
      },
      label: {
        sentence: "",
        // For a formal, club-notice feel on a primary CTA — see
        // docs/STYLE_GUIDE.md's Buttons section for when to use this vs.
        // leaving a button in sentence case.
        overline: "tracking-[0.1em] uppercase",
      },
      size: {
        default:
          "h-8 gap-1.5 px-2.5 has-data-[icon=inline-end]:pr-2 has-data-[icon=inline-start]:pl-2",
        xs: "h-6 gap-1 rounded-[min(var(--radius-md),10px)] px-2 text-xs in-data-[slot=button-group]:rounded-lg has-data-[icon=inline-end]:pr-1.5 has-data-[icon=inline-start]:pl-1.5 [&_svg:not([class*='size-'])]:size-3",
        sm: "h-7 gap-1 rounded-[min(var(--radius-md),12px)] px-2.5 text-[0.8rem] in-data-[slot=button-group]:rounded-lg has-data-[icon=inline-end]:pr-1.5 has-data-[icon=inline-start]:pl-1.5 [&_svg:not([class*='size-'])]:size-3.5",
        lg: "h-9 gap-1.5 px-2.5 has-data-[icon=inline-end]:pr-2 has-data-[icon=inline-start]:pl-2",
        icon: "size-8",
        "icon-xs":
          "size-6 rounded-[min(var(--radius-md),10px)] in-data-[slot=button-group]:rounded-lg [&_svg:not([class*='size-'])]:size-3",
        "icon-sm":
          "size-7 rounded-[min(var(--radius-md),12px)] in-data-[slot=button-group]:rounded-lg",
        "icon-lg": "size-9",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
      label: "sentence",
    },
  }
)

function Button({
  className,
  variant = "default",
  size = "default",
  label = "sentence",
  ...props
}: ButtonPrimitive.Props & VariantProps<typeof buttonVariants>) {
  return (
    <ButtonPrimitive
      data-slot="button"
      className={cn(buttonVariants({ variant, size, label, className }))}
      {...props}
    />
  )
}

export { Button, buttonVariants }
