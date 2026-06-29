interface ToolbarProps {
  onFitView: () => void
}

export default function Toolbar({ onFitView }: ToolbarProps) {
  return (
    <div className="toolbar">
      <button type="button" onClick={onFitView}>
        Fit to screen
      </button>
    </div>
  )
}
