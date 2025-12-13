interface Props {
  name: string;
  value: string;
  description: string;
  handleFunction: (option: string | null) => void;
  children: React.ReactNode;
}

export default function SelectField({
  name,
  value,
  description,
  handleFunction,
  children,
}: Props) {
  return (
    <>
      <label className="sr-only" htmlFor={name}>
        {name}
      </label>
      <select
        id={name}
        name={name}
        value={value || ""}
        onChange={(event) => handleFunction(event.target.value)}
        required
      >
        <option value="" disabled>
          {description}
        </option>
        {children}
      </select>
    </>
  );
}
