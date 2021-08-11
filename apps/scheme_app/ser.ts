interface IBotDialog {
  class: string
  data: { [key: string]: string }
  html: string
  id: number
  name: string
  inputs: {
    [name: string]: {
      connections: {
        node: string
        input: string
      }[]
    }
  }
  outputs: {
    [name: string]: {
      connections: {
        node: string
        output: string
      }[]
    }
  }
  pos_x: number
  pos_y: number
  typenode: string
}
