export default function ThanksPage() {
  return (
    <div className="mx-auto flex max-w-4xl flex-col gap-12 px-8 py-20 text-center">
      <section className="flex flex-col gap-6">
        <h1 className="text-4xl font-bold text-[#1C1C1C]">Acknowledgements</h1>
        <p className="text-lg leading-relaxed text-[#4B5563]">
          This project was made possible by the support of an incredible community.
        </p>
      </section>

      <section className="flex flex-col gap-6 text-center">
        <p className="text-lg leading-relaxed text-[#4B5563]">
          We extend our deepest gratitude to <strong>Fabien</strong> and{" "}
          <strong>Yousouf</strong> of the Wimmics team at Inria, true pioneers
          of the Semantic Web. Their foundational work on{" "}
          <strong>gen2kgbot</strong> provided the engine for our agent, and their
          global leadership in the field is a constant inspiration.
        </p>
        <p className="text-lg leading-relaxed text-[#4B5563]">
          Our sincere thanks to <strong>Smaël</strong>, <strong>Yohan</strong>,
          and <strong>Luc</strong> from the Pasteur community. Their invaluable
          medical expertise, sharp feedback, and enthusiasm for exploring these
          challenges with us were instrumental in grounding our project in a
          real-world context.
        </p>
        <p className="text-lg leading-relaxed text-[#4B5563]">
          Thank you to <strong>Julien Calenge</strong>, Head of Epitech Lyon, for
          his guidance and support.
        </p>
        <p className="text-lg leading-relaxed text-[#4B5563]">
          A special thanks to <strong>Google Cloud</strong> for providing the
          platform and resources that powered our development.
        </p>
      </section>

      <section className="flex flex-col gap-6 text-center">
        <p className="text-lg leading-relaxed text-[#4B5563]">
          And finally, this project is the result of a marathon collaboration by
          our team:
        </p>
        <div className="mx-auto flex max-w-md flex-col gap-2">
          <p className="text-base font-medium text-[#1C1C1C]">Léandre Ramos</p>
          <p className="text-base font-medium text-[#1C1C1C]">Spencer Pay</p>
          <p className="text-base font-medium text-[#1C1C1C]">Youssef Mehili</p>
          <p className="text-base font-medium text-[#1C1C1C]">Sacha Henneveux</p>
          <p className="text-base font-medium text-[#1C1C1C]">Antoine Béal</p>
        </div>
      </section>
    </div>
  );
}
